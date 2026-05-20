from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse, FileResponse, RedirectResponse
from fastapi import WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import base64
import hmac
import hashlib
import secrets
import time
import os
import logging
from logging.handlers import RotatingFileHandler
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from twilio.rest import Client
from gemini_ai import GeminiLiveSession, convert_mulaw_to_pcm16, convert_pcm16_to_mulaw, resample_audio
from google import genai
from voice_pipeline import VoicePipeline
from database import init_db, get_db
from sqlalchemy.orm import Session
from models import User
from call_service import call_service
from audio_recorder import AudioRecorder
from typing import Optional

# Configure logging (console + file)
os.makedirs("logs", exist_ok=True)
log_file = os.path.join("logs", "app.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3),
    ],
)
logger = logging.getLogger(__name__)

# Load environment variables (ensure we read the project .env even if cwd differs)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(BASE_DIR, ".env")
PARENT_ENV = os.path.join(BASE_DIR, "..", ".env")
# Shell/env wins over .env so scripts (e.g. start.sh + ngrok) can set TUNNEL_LINK.
load_dotenv(PARENT_ENV, override=False)
load_dotenv(DOTENV_PATH, override=False)


def _ensure_google_application_credentials() -> None:
    """Point GOOGLE_APPLICATION_CREDENTIALS at a real file (fixes stale absolute paths)."""
    raw = (os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip().strip('"').strip("'")
    if not raw:
        return
    path = raw
    if not os.path.isabs(path):
        path = os.path.normpath(os.path.join(BASE_DIR, path))
    if not os.path.isfile(path):
        name = os.path.basename(raw.rstrip("/"))
        if name.endswith(".json"):
            alt = os.path.join(BASE_DIR, "google", name)
            if os.path.isfile(alt):
                logger.warning(
                    "GOOGLE_APPLICATION_CREDENTIALS not found at %s; using %s",
                    raw,
                    alt,
                )
                path = alt
    if os.path.isfile(path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(path)
    else:
        logger.error(
            "GOOGLE_APPLICATION_CREDENTIALS file missing (last tried: %s)",
            path,
        )


_ensure_google_application_credentials()

# Twilio / call audio: set RECORD_CALL_AUDIO=1 to save WAVs again
RECORD_CALL_AUDIO = os.getenv("RECORD_CALL_AUDIO", "0").strip().lower() in (
    "1",
    "true",
    "yes",
)

# Initialize database
init_db()
logger.info("Database initialized")

app = FastAPI()

# --- Auth & RBAC Helpers ---
AUTH_SECRET = os.getenv("AUTH_SECRET") or secrets.token_hex(32)
TOKEN_COOKIE = "access_token"
AUTH_DEBUG = (os.getenv("AUTH_DEBUG", "0") == "1")

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _b64url_json(obj: dict) -> str:
    return _b64url(json.dumps(obj, separators=(",", ":")).encode())

def _b64url_decode(s: str) -> bytes:
    pad = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def create_token(sub: str, role: str, ttl_minutes: int = 7 * 24 * 60) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {"sub": sub, "role": role, "iat": now, "exp": now + ttl_minutes * 60}
    signing_input = f"{_b64url_json(header)}.{_b64url_json(payload)}".encode()
    signature = hmac.new(AUTH_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{signing_input.decode()}.{_b64url(signature)}"

from typing import Optional as _Optional

def verify_token(token: str) -> _Optional[dict]:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        signing_input = f"{parts[0]}.{parts[1]}".encode()
        sig = _b64url_decode(parts[2])
        expected = hmac.new(AUTH_SECRET.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_b64url_decode(parts[1]).decode())
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

def hash_password(password: str, salt: _Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{digest}"

def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, digest = password_hash.split(":", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == digest
    except Exception:
        return False

def get_user_by_username(db: Session, username: str) -> _Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_current_user(request: Request) -> _Optional[User]:
    token = request.cookies.get(TOKEN_COOKIE)
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        return None
    username = payload.get("sub")
    if not username:
        return None
    with get_db() as db:
        user = get_user_by_username(db, username)
        if user and user.is_active:
            return user
    return None

def seed_default_users():
    try:
        with get_db() as db:
            any_user = db.query(User).first()
            if any_user:
                logger.info("User seeding skipped: users already present")
                return
            admins = [
                {"name": "Amit Sharma", "username": "amit.sharma", "email": "amit.sharma@example.in", "phone": "+919876543210", "role": "admin"},
                {"name": "Priya Iyer", "username": "priya.iyer", "email": "priya.iyer@example.in", "phone": "+918765432109", "role": "admin"},
            ]
            cses = [
                {"name": "Rohit Verma", "username": "rohit.verma", "email": "rohit.verma@example.in", "phone": "+919112233445", "role": "cse"},
                {"name": "Neha Gupta", "username": "neha.gupta", "email": "neha.gupta@example.in", "phone": "+919556677889", "role": "cse"},
            ]
            default_password = os.getenv("DEFAULT_USER_PASSWORD", "ChangeMe@123")
            if AUTH_DEBUG:
                logger.warning("AUTH_DEBUG: Seeding users with default password: %s", default_password)
            for u in admins + cses:
                db.add(User(
                    name=u["name"],
                    username=u["username"],
                    email=u["email"],
                    phone=u["phone"],
                    role=u["role"],
                    password_hash=hash_password(default_password),
                    is_active=True,
                ))
            db.commit()
            logger.info("Seeded default users: %s", ", ".join([u["username"] for u in admins + cses]))
    except Exception as e:
        logger.error(f"User seeding failed: {e}")

# Seed users on startup
seed_default_users()
# --- Transfer Helpers ---
def detect_transfer_intent(user_text: str) -> bool:
    """Detect if user wants to transfer to a human agent based on their speech."""
    if not user_text:
        return False
    
    text_lower = user_text.lower().strip()
    
    # Only explicit transfer requests should trigger escalation
    transfer_keywords = [
        "transfer me",
        "transfer the call",
        "transfer my call",
        "connect me to a human",
        "connect me to an agent",
        "connect me to a representative",
        "speak to a human",
        "talk to a human",
        "speak to an agent",
        "talk to an agent",
        "real person",
        "human agent",
        "live agent",
        "operator",
        "supervisor",
    ]
    
    # Check if user text contains any transfer keywords
    for keyword in transfer_keywords:
        if keyword in text_lower:
            logger.info(f"Transfer intent detected: '{keyword}' in user speech: '{user_text}'")
            return True
    
    return False


def resolve_call_sid_by_stream(stream_sid: Optional[str]) -> Optional[str]:
    """Resolve a call SID from a stream SID using the database."""
    if not stream_sid:
        return None
    try:
        with get_db() as db:
            call = call_service.get_call_by_stream_sid(db, stream_sid)
            return call.call_sid if call else None
    except Exception as e:
        logger.error(f"Failed to resolve call SID by stream SID {stream_sid}: {e}")
        return None


async def initiate_transfer(call_sid: str, stream_sid: Optional[str] = None) -> bool:
    """Initiate transfer for the given call SID with robust fallback logic."""
    try:
        if not call_sid:
            call_sid = resolve_call_sid_by_stream(stream_sid)
        if not call_sid:
            logger.error("No call SID available to transfer")
            return False

        transfer_url = f"{TUNNEL_LINK.rstrip('/')}/twilio/transfer"

        # Mark status as transferring in DB
        try:
            with get_db() as db:
                call_service.update_call_status(db, call_sid, "transferring")
        except Exception as e:
            logger.warning(f"Could not set DB status to transferring for {call_sid}: {e}")

        # Attempt redirect via URL first
        try:
            updated = await asyncio.to_thread(
                twilio_client.calls(call_sid).update,
                url=transfer_url,
                method="POST",
            )
            logger.info(f"Twilio redirect via URL succeeded. Call status: {getattr(updated, 'status', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Redirect via URL failed: {e}")

        # Fallback: provide TwiML directly
        try:
            twiml = f"""
            <Response>
                <Say>Please hold while I connect you to a human agent.</Say>
                <Dial callerId="{PHONE_NO}">{HUMAN_AGENT_NUMBER}</Dial>
            </Response>
            """
            updated = await asyncio.to_thread(
                twilio_client.calls(call_sid).update,
                twiml=twiml,
            )
            logger.info(f"Twilio update via TwiML succeeded. Call status: {getattr(updated, 'status', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Fallback TwiML update failed: {e}")
            return False
    except Exception as e:
        logger.error(f"initiate_transfer unexpected error: {e}")
        return False

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Twilio credentials (KrishiMitra_syngenta .env names supported)
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID") or os.getenv("ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN") or os.getenv("AUTH_TOKEN")
PHONE_NO = os.getenv("TWILIO_PHONE_NUMBER") or os.getenv("PHONE_NO")
HUMAN_AGENT_NUMBER = os.getenv("HUMAN_AGENT_NUMBER", "+917904456026")
# HUMAN_AGENT_NUMBER = "+919943193399"


# Gemini API
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY is missing or empty (checked GEMINI_API_KEY/GOOGLE_API_KEY).")
def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}****{key[-4:]}"

# Voice Engine Configuration
# Options: "gemini_live" (default) or "pipeline" (STT->LLM->TTS)
VOICE_ENGINE = os.getenv("VOICE_ENGINE", "gemini_live").lower()
LIVE_API_ENABLED = (os.getenv("LIVE_API") or os.getenv("live_api") or "").strip().lower() in ("1", "true", "yes", "y", "on")
LIVE_API_MODEL = (os.getenv("LIVE_API_MODEL") or os.getenv("live_api_model") or "").strip()
PIPELINE_LLM_MODEL = (os.getenv("LLM_MODEL") or "gemini-3-flash-preview").strip()

logger.info(
    "Voice engine: %s | live_api=%s%s",
    VOICE_ENGINE,
    LIVE_API_ENABLED,
    (f" model={LIVE_API_MODEL}" if (LIVE_API_ENABLED and LIVE_API_MODEL) else ""),
)
if VOICE_ENGINE != "gemini_live" and LIVE_API_ENABLED:
    logger.warning("LIVE_API is enabled but VOICE_ENGINE=%s, so Live API will NOT be used.", VOICE_ENGINE)
if VOICE_ENGINE == "pipeline":
    logger.info("Pipeline LLM model: %s | STT=%s | TTS=%s", PIPELINE_LLM_MODEL, os.getenv("STT_PROVIDER", "google"), os.getenv("TTS_PROVIDER", "google"))

# Tunnel link (ngrok or devtunnels) — align with KrishiMitra_syngenta .env
TUNNEL_LINK = (
    os.getenv("TUNNEL_LINK")
    or os.getenv("NGROK_PUBLIC_URL")
    or os.getenv("PUBLIC_VOICE_BASE_URL")
    or os.getenv("NGROK_VOICE_BASE_URL")
    or "https://localhost:8000"
).rstrip("/")

# Load persona for the AI agent
def load_persona():
    """Load the AI agent persona from config/persona.txt"""
    persona_path = os.path.join(BASE_DIR, "config", "persona.txt")
    try:
        with open(persona_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning("config/persona.txt not found, using default system instruction")
        return (
            "You are KrishiMitra, a trusted agricultural advisory voice assistant for Indian farmers. "
            "Speak simply and warmly. CRITICAL: reply in the farmer's preferred language from context."
        )

AGENT_PERSONA = load_persona()


# Initialize Twilio client
twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)

# KrishiMitra voice routes (farmer context + POST /krishimitra/call)
from krishimitra import routes as krishimitra_routes
from krishimitra.context import build_system_instruction, build_phone_intro, escape_twiml_say
from krishimitra.store import get as get_call_context
from krishimitra.store import pop as pop_call_context

app.include_router(krishimitra_routes.router)
krishimitra_routes.configure_twilio(twilio_client, PHONE_NO or "", TUNNEL_LINK)

# Store active Gemini sessions
gemini_sessions = {}

class CallRequest(BaseModel):
    to_number: str
    from_number: Optional[str] = None

class CallbackRequest(BaseModel):
    agent_phone: str  # Agent's phone number
    customer_phone: str  # Customer phone number

class AgentCallRequest(BaseModel):
    customer_phone: str  # Customer phone number to call

@app.get("/")
async def root():
    with open("index.html", "r") as f:
        html_content = f.read()
    return Response(content=html_content, media_type="text/html")


@app.get("/login")
async def login_page():
    try:
        with open("login.html", "r") as f:
            html = f.read()
        return Response(content=html, media_type="text/html")
    except FileNotFoundError:
        return Response(content="<h1>Login</h1>", media_type="text/html")


@app.post("/auth/login")
async def auth_login(request: Request):
    form = await request.form()
    username = (form.get("username") or "").strip()
    password = (form.get("password") or "")
    if AUTH_DEBUG:
        logger.warning("AUTH_DEBUG: Login attempt username='%s' password='%s'", username, password)
    if not username or not password:
        return JSONResponse(status_code=400, content={"success": False, "error": "Username and password are required"})

    with get_db() as db:
        user = db.query(User).filter(User.username == username, User.is_active == True).first()
        if not user:
            logger.warning("Login failed: user not found or inactive - username='%s'", username)
            return JSONResponse(status_code=401, content={"success": False, "error": "Invalid credentials"})

        if not verify_password(password, user.password_hash):
            logger.warning("Login failed: bad password - username='%s'", username)
            if AUTH_DEBUG:
                try:
                    salt, stored_digest = user.password_hash.split(":", 1)
                    computed_digest = hashlib.sha256((salt + password).encode()).hexdigest()
                    logger.warning(
                        "AUTH_DEBUG: Password mismatch details username='%s' salt='%s' computed='%s' stored='%s'",
                        username, salt, computed_digest, stored_digest
                    )
                except Exception as e:
                    logger.error("AUTH_DEBUG: Failed hash debug for '%s': %s", username, e)
            return JSONResponse(status_code=401, content={"success": False, "error": "Invalid credentials"})

        token = create_token(user.username, user.role)
        resp = JSONResponse(content={"success": True, "message": "Logged in", "role": user.role, "name": user.name})
        # Set HttpOnly cookie
        resp.set_cookie(
            key=TOKEN_COOKIE,
            value=token,
            httponly=True,
            samesite="lax",
            secure=False
        )
        return resp


@app.get("/auth/debug/users")
async def auth_debug_users():
    try:
        with get_db() as db:
            users = db.query(User).all()
            return JSONResponse(content={
                "count": len(users),
                "users": [
                    {"username": u.username, "role": u.role, "active": u.is_active}
                    for u in users
                ]
            })
    except Exception as e:
        logger.error("/auth/debug/users error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/auth/debug/reset-password")
async def auth_debug_reset_password(request: Request):
    if not AUTH_DEBUG:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    data = await request.json()
    username = (data.get("username") or "").strip()
    new_password = data.get("new_password") or os.getenv("DEFAULT_USER_PASSWORD", "ChangeMe@123")
    if not username:
        return JSONResponse(status_code=400, content={"error": "username is required"})
    try:
        with get_db() as db:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return JSONResponse(status_code=404, content={"error": "user not found"})
            user.password_hash = hash_password(new_password)
            db.commit()
            logger.warning("AUTH_DEBUG: Password reset for '%s' to '%s'", username, new_password)
            return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error("/auth/debug/reset-password error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/auth/me")
async def auth_me(request: Request):
    token = request.cookies.get(TOKEN_COOKIE)
    if not token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    
    payload = verify_token(token)
    if not payload:
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    
    username = payload.get("sub")
    if not username:
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    
    # Fetch and serialize inside session context to avoid DetachedInstanceError
    with get_db() as db:
        user = db.query(User).filter(User.username == username, User.is_active == True).first()
        if not user:
            return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
        user_data = user.to_public_dict()
    
    return JSONResponse(content={"success": True, "user": user_data})


@app.get("/logout")
async def logout():
    resp = RedirectResponse(url="/login")
    resp.delete_cookie(TOKEN_COOKIE)
    return resp


@app.get("/dashboard")
async def dashboard(request: Request):
    """Call dashboard - view all calls, recordings, and transcripts"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    try:
        with open("dashboard.html", "r") as f:
            html_content = f.read()
    except FileNotFoundError:
        html_content = "<h1>Dashboard</h1>"
    return Response(content=html_content, media_type="text/html")

@app.post("/make-call")
async def make_call(call_request: CallRequest):
    try:
        logger.info(f"📞 Attempting to call: {call_request.to_number} from {PHONE_NO}")
        
        # Initiate call using Twilio with ngrok webhook
        call = twilio_client.calls.create(
            to=call_request.to_number,
            from_=PHONE_NO,
            url=f"{TUNNEL_LINK.rstrip('/')}/twilio/voice",
            status_callback=f"{TUNNEL_LINK.rstrip('/')}/twilio/status",
            status_callback_event=["initiated", "ringing", "answered", "completed", "busy", "failed", "no-answer"]
        )
        
        logger.info(f"✅ Call created successfully! SID: {call.sid}")
        
        # Log call to database
        with get_db() as db:
            call_service.create_call(
                db=db,
                call_sid=call.sid,
                direction="outbound",
                from_number=PHONE_NO,
                to_number=call_request.to_number,
                status=call.status
            )
        
        return JSONResponse(
            content={
                "success": True,
                "call_sid": call.sid,
                "status": call.status,
                "message": f"Call initiated to {call_request.to_number}"
            }
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error creating call: {error_msg}")
        
        # Parse Twilio-specific errors
        user_friendly_msg = error_msg
        if "21219" in error_msg or "unverified" in error_msg.lower():
            user_friendly_msg = f"The number {call_request.to_number} is not verified. Please verify it in your Twilio console first."
        elif "21212" in error_msg:
            user_friendly_msg = "The 'From' phone number is not a valid Twilio number."
        elif "21211" in error_msg:
            user_friendly_msg = "Invalid 'To' phone number format."
        elif "21608" in error_msg:
            user_friendly_msg = "The phone number is not capable of receiving calls."
        
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": user_friendly_msg,
                "error_code": "TWILIO_ERROR"
            }
        )

# RESTful API endpoint for callback requests
@app.post("/api/v1/callback")
async def request_callback(callback_request: CallbackRequest):
    """
    RESTful API endpoint to request a callback.
    Calls the AGENT first from Twilio number, then connects to CUSTOMER.
    POST /api/v1/callback with JSON body: 
    {
        "agent_phone": "+1234567890",
        "customer_phone": "+919147196925"
    }
    """
    try:
        agent_phone = callback_request.agent_phone
        customer_phone = callback_request.customer_phone
        
        logger.info(f"Callback: Agent {agent_phone} calling Customer {customer_phone}")
        
        # Create TwiML for the call
        from twilio.twiml.voice_response import VoiceResponse
        
        response = VoiceResponse()
        response.say(f"Connecting you to the customer at {customer_phone}")
        
        # Dial the customer
        response.dial(customer_phone, timeout=30)
        
        # Initiate call to AGENT from Twilio number
        call = twilio_client.calls.create(
            to=agent_phone,
            from_=PHONE_NO,
            twiml=str(response),
            status_callback=f"{TUNNEL_LINK.rstrip('/')}/twilio/status",
            status_callback_event=["initiated", "ringing", "answered", "completed", "busy", "failed", "no-answer"]
        )
        
        logger.info(f"Callback call initiated to agent {agent_phone}! SID: {call.sid}")
        
        # Log call to database
        with get_db() as db:
            call_service.create_call(
                db=db,
                call_sid=call.sid,
                direction="outbound",
                from_number=PHONE_NO,
                to_number=customer_phone,
                status=call.status
            )
        
        return JSONResponse(
            status_code=201,
            content={
                "success": True,
                "call_sid": call.sid,
                "status": call.status,
                "agent_phone": agent_phone,
                "customer_phone": customer_phone,
                "twilio_number": PHONE_NO,
                "message": f"Calling agent {agent_phone} to connect with customer {customer_phone}"
            }
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Callback error: {error_msg}")
        
        # Parse errors
        user_friendly_msg = error_msg
        status_code = 400
        
        if "21219" in error_msg or "unverified" in error_msg.lower():
            user_friendly_msg = f"Phone number not verified. Trial accounts can only call verified numbers."
            status_code = 403
        elif "21212" in error_msg:
            user_friendly_msg = "Invalid Twilio phone number configuration."
            status_code = 500
        elif "21211" in error_msg:
            user_friendly_msg = "Invalid phone number format. Use E.164 format (e.g., +1234567890)."
            status_code = 422
        elif "21608" in error_msg:
            user_friendly_msg = "This phone number cannot receive calls."
            status_code = 400
        
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": user_friendly_msg,
                "error_code": "CALLBACK_FAILED",
                "to_number": callback_request.customer_phone
            }
        )


@app.post("/agent-call")
async def agent_call(call_request: AgentCallRequest):
    """
    Initiate a call for agent to handle through browser.
    Like /make-call, but the agent will handle it via WebSocket.
    
    POST /agent-call with JSON body:
    {
        "customer_phone": "+919147196925"
    }
    """
    try:
        customer_phone = call_request.customer_phone
        
        # DEBUG LOGS
        logger.info(f"========== AGENT CALL REQUEST DEBUG ==========")
        logger.info(f"Full request: {call_request}")
        logger.info(f"Customer phone value: '{customer_phone}'")
        logger.info(f"Customer phone type: {type(customer_phone)}")
        logger.info(f"Twilio FROM number: '{PHONE_NO}'")
        logger.info(f"Will call TO number: '{customer_phone}'")
        logger.info(f"============================================")
        
        # Validate
        if not customer_phone or len(customer_phone.strip()) == 0:
            logger.error(f"ERROR: Customer phone is empty or None!")
            raise ValueError("Customer phone number is required")
        
        logger.info(f"Creating Twilio call: FROM={PHONE_NO} TO={customer_phone} URL={TUNNEL_LINK.rstrip('/')}/twilio/agent-voice")
        
        # Initiate outbound call TO customer FROM Twilio number
        call = twilio_client.calls.create(
            to=customer_phone,
            from_=PHONE_NO,
            url=f"{TUNNEL_LINK.rstrip('/')}/twilio/agent-voice",
            status_callback=f"{TUNNEL_LINK.rstrip('/')}/twilio/status",
            status_callback_event=["initiated", "ringing", "answered", "completed", "busy", "failed", "no-answer"]
        )
        
        logger.info(f"✓ TWILIO CALL CREATED SUCCESSFULLY")
        logger.info(f"  Call SID: {call.sid}")
        logger.info(f"  Twilio created call TO: {call.to}")
        logger.info(f"  Status: {call.status}")
        
        # Log call to database
        with get_db() as db:
            call_service.create_call(
                db=db,
                call_sid=call.sid,
                direction="outbound",
                from_number=PHONE_NO,
                to_number=customer_phone,
                status=call.status
            )
        
        logger.info(f"✓ Call logged to database")
        
        return JSONResponse(
            status_code=201,
            content={
                "success": True,
                "call_sid": call.sid,
                "status": call.status,
                "customer_phone": customer_phone,
                "twilio_number": PHONE_NO,
                "message": f"Call initiated to {customer_phone}. Connect agent browser session."
            }
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Agent call error: {error_msg}")
        
        # Parse errors
        user_friendly_msg = error_msg
        status_code = 400
        
        if "21219" in error_msg or "unverified" in error_msg.lower():
            user_friendly_msg = f"Phone number not verified in Twilio."
            status_code = 403
        elif "21211" in error_msg:
            user_friendly_msg = "Invalid phone number format. Use E.164 format."
            status_code = 422
        
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": user_friendly_msg,
                "error_code": "AGENT_CALL_FAILED",
                "customer_phone": customer_phone
            }
        )


@app.post("/twilio/agent-voice")
async def twilio_agent_voice(request: Request):
    """Handle inbound agent calls - connect to agent WebSocket"""
    
    # Parse form data from Twilio
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    from_number = form_data.get("From")
    to_number = form_data.get("To")
    
    logger.info(f"Agent call received from {from_number} to {to_number} (SID: {call_sid})")
    
    # Log or update call in database
    if call_sid:
        with get_db() as db:
            existing_call = call_service.get_call_by_sid(db, call_sid)
            if existing_call:
                call_service.update_call_status(db, call_sid, "ringing")
                logger.info(f"Updated agent call {call_sid} status to ringing")
            else:
                call_service.create_call(
                    db=db,
                    call_sid=call_sid,
                    direction="inbound",
                    from_number=from_number or "unknown",
                    to_number=to_number or PHONE_NO,
                    status="ringing"
                )
    
    # Ensure we don't end up with double slashes in the WebSocket URL
    ws_url = (
        TUNNEL_LINK.rstrip("/")
        .replace("https://", "wss://")
        .replace("http://", "ws://")
        + "/ws/agent-call"
    )
    twiml = f"""
    <Response>
        <Say>Connecting you to an agent.</Say>
        <Connect>
            <Stream url="{ws_url}"/>
        </Connect>
    </Response>
    """
    return Response(content=twiml, media_type="application/xml")


# Dictionary to track agent call sessions
agent_call_sessions = {}


@app.websocket("/ws/agent-call")
async def agent_call_stream(ws: WebSocket):
    """
    WebSocket handler for agent call handling.
    Agent's browser mic/speaker connects here.
    Audio from customer goes to agent's speaker.
    Audio from agent's mic goes to customer.
    """
    await ws.accept()
    logger.info("Agent call connected - WebSocket established")
    
    stream_sid = None
    call_sid = None
    
    try:
        while True:
            message = await ws.receive_text()
            data = json.loads(message)
            event = data.get("event")

            if event == "start":
                stream_sid = data["start"]["streamSid"]
                call_sid = data["start"].get("callSid")
                logger.info(f"Agent call stream started: {stream_sid} (Call: {call_sid})")
                
                # Update call status
                if call_sid:
                    with get_db() as db:
                        call_service.update_call_status(db, call_sid, "in-progress")
                
                # Store session
                agent_call_sessions[stream_sid] = {
                    "call_sid": call_sid,
                    "stream_sid": stream_sid,
                    "connected_at": datetime.now()
                }
                
                # Send media response
                await ws.send_text(json.dumps({
                    "event": "connected",
                    "message": "Agent session established"
                }))

            elif event == "media":
                # Audio from customer -> agent's speaker
                payload = data["media"]["payload"]
                
                # Convert from mulaw to PCM for agent's audio
                try:
                    audio_data = base64.b64decode(payload)
                    # Audio is ready for agent's browser to play
                    # Browser receives this via audio context
                except Exception as e:
                    logger.warning(f"Audio decode error: {e}")

            elif event == "dtmf":
                # Handle DTMF (keypad) input from agent
                digit = data.get("dtmf", {}).get("digit")
                logger.info(f"Agent pressed digit: {digit}")

            elif event == "stop":
                logger.info(f"Agent call stream stopped: {stream_sid}")
                
                # Update call status to completed
                if call_sid:
                    with get_db() as db:
                        call_service.update_call_status(db, call_sid, "completed")
                
                # Clean up session
                if stream_sid in agent_call_sessions:
                    del agent_call_sessions[stream_sid]
                break

    except Exception as e:
        logger.error(f"Agent call error: {e}")
        
        # Update call status on error
        if call_sid:
            with get_db() as db:
                call_service.update_call_status(db, call_sid, "failed")
        
        # Clean up session
        if stream_sid and stream_sid in agent_call_sessions:
            del agent_call_sessions[stream_sid]
    
    logger.info("Agent call session closed")


# Call Management API Endpoints

@app.get("/api/v1/calls")
async def list_calls(
    skip: int = 0,
    limit: int = 100,
    direction: Optional[str] = None,
    status: Optional[str] = None
):
    """
    List all calls with optional filters
    
    Query Parameters:
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    - direction: Filter by direction (inbound/outbound)
    - status: Filter by status (queued/in-progress/completed/failed)
    """
    with get_db() as db:
        calls = call_service.get_all_calls(
            db=db,
            skip=skip,
            limit=limit,
            direction=direction,
            status=status
        )
        return JSONResponse(
            content={
                "success": True,
                "count": len(calls),
                "calls": [call.to_dict() for call in calls]
            }
        )


@app.get("/api/v1/calls/stats")
async def get_call_stats():
    """Get call statistics"""
    with get_db() as db:
        stats = call_service.get_call_stats(db)
        return JSONResponse(
            content={
                "success": True,
                "stats": stats
            }
        )


@app.get("/api/v1/calls/{call_sid}")
async def get_call(call_sid: str):
    """Get details of a specific call by SID"""
    with get_db() as db:
        call = call_service.get_call_by_sid(db, call_sid)
        if not call:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Call not found"
                }
            )
        return JSONResponse(
            content={
                "success": True,
                "call": call.to_dict()
            }
        )


@app.get("/api/v1/intent/stats")
async def get_intent_stats():
    """Get intent analysis statistics"""
    with get_db() as db:
        intent_stats = call_service.get_intent_stats(db)
        return JSONResponse(
            content={
                "success": True,
                "intent_stats": intent_stats
            }
        )


@app.get("/api/v1/intent/breakdown")
async def get_intent_breakdown():
    """Get intent statistics breakdown for all intent types"""
    with get_db() as db:
        breakdown = call_service.get_all_intent_breakdown(db)
        return JSONResponse(
            content={
                "success": True,
                "breakdown": breakdown
            }
        )


@app.get("/api/v1/calls/by-intent/{intent_category}")
async def get_calls_by_intent(intent_category: str, limit: int = 50):
    """Get calls filtered by intent category (high, medium, low)"""
    if intent_category not in ["high", "medium", "low"]:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Invalid intent category. Must be high, medium, or low"
            }
        )
    
    with get_db() as db:
        calls = call_service.get_calls_by_intent(db, intent_category, limit)
        return JSONResponse(
            content={
                "success": True,
                "category": intent_category,
                "count": len(calls),
                "calls": [call.to_dict() for call in calls]
            }
        )


@app.post("/api/v1/calls/{call_sid}/analyze-intent")
async def analyze_call_intent(call_sid: str):
    """
    Analyze intent from call transcript and update call record
    """
    with get_db() as db:
        call = call_service.get_call_by_sid(db, call_sid)
        if not call:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Call not found"
                }
            )
        
        # Combine all transcript text
        transcript_text = " ".join([
            entry.get("text", "") for entry in (call.transcript or [])
        ])
        
        # Calculate intent score
        intent_result = call_service.calculate_intent_score(transcript_text)
        
        # Update call with intent score
        call_service.set_intent_score(
            db,
            call_sid,
            intent_result["score"],
            intent_result["category"]
        )
        
        return JSONResponse(
            content={
                "success": True,
                "call_sid": call_sid,
                "intent_score": intent_result["score"],
                "intent_category": intent_result["category"]
            }
        )


@app.get("/api/v1/recordings/{call_sid}")
async def get_recording(call_sid: str):
    """
    Get recording information for a call.
    Returns full call details including transcript and recording path.
    """
    with get_db() as db:
        call = call_service.get_call_by_sid(db, call_sid)
        if not call:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Call not found"
                }
            )
        
        # Return complete call details
        return JSONResponse(
            content={
                "success": True,
                "call": call.to_dict()
            }
        )


@app.get("/api/v1/recordings/{call_sid}/download")
async def download_recording(call_sid: str):
    """Download call recording audio file"""
    with get_db() as db:
        call = call_service.get_call_by_sid(db, call_sid)
        if not call or not call.recording_path:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Recording not found"
                }
            )
        
        if not os.path.exists(call.recording_path):
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Recording file not found on disk"
                }
            )
        
        return FileResponse(
            path=call.recording_path,
            media_type="audio/wav",
            filename=f"{call_sid}.wav"
        )


@app.get("/api/v1/gemini/models")
async def list_gemini_models():
    """List available Gemini models for the configured API key."""
    if not GEMINI_API_KEY:
        return JSONResponse(status_code=400, content={"success": False, "error": "GEMINI_API_KEY is missing"})
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        models = []
        for m in client.models.list():
            models.append({
                "name": getattr(m, "name", None),
                "display_name": getattr(m, "display_name", None),
                "supported_methods": getattr(m, "supported_methods", None),
            })
        return JSONResponse(content={"success": True, "models": models})
    except Exception as e:
        logger.error("Failed to list Gemini models: %s", e)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "key_hint": _mask_key(GEMINI_API_KEY),
                "key_length": len(GEMINI_API_KEY),
            },
        )


@app.get("/api/v1/gemini/key-info")
async def gemini_key_info():
    """Return masked Gemini key info for debugging without exposing secrets."""
    return JSONResponse(
        content={
            "success": True,
            "key_hint": _mask_key(GEMINI_API_KEY),
            "key_length": len(GEMINI_API_KEY),
        }
    )



# @app.post("/twilio/voice")
# async def twilio_voice(request: Request):
#     twiml = """
#     <Response>
#         <Gather input="dtmf" numDigits="1" timeout="5">
#             <Say>
#                 Press any key to continue to customer support.
#             </Say>
#         </Gather>
#         <Say>No input received. Goodbye.</Say>
#     </Response>
#     """
#     return Response(content=twiml, media_type="application/xml")

@app.post("/twilio/voice")
@app.get("/twilio/voice")
async def twilio_voice(request: Request):
    """Handle inbound/outbound calls — connect Media Stream to Gemini (KrishiMitra)."""
    
    # Parse form data from Twilio
    form_data = await request.form() if request.method == "POST" else {}
    call_sid = form_data.get("CallSid")
    from_number = form_data.get("From")
    to_number = form_data.get("To")
    context_id = request.query_params.get("context_id") or ""
    
    logger.info(
        f"📞 Voice webhook from {from_number} to {to_number} (SID: {call_sid}, context_id={context_id})"
    )
    
    # Log or update call in database
    if call_sid:
        with get_db() as db:
            # Check if call already exists (e.g., outbound call we initiated)
            existing_call = call_service.get_call_by_sid(db, call_sid)
            if existing_call:
                # Update status for existing call (outbound that's now connecting)
                call_service.update_call_status(db, call_sid, "ringing")
                logger.info(f"Updated existing call {call_sid} status to ringing")
            else:
                # Create new record for true inbound call
                call_service.create_call(
                    db=db,
                    call_sid=call_sid,
                    direction="inbound",
                    from_number=from_number or "unknown",
                    to_number=to_number or PHONE_NO,
                    status="ringing"
                )
    
    ws_url = TUNNEL_LINK.replace("https://", "wss://").replace("http://", "ws://").rstrip("/") + "/ws/call"
    param_xml = ""
    if context_id:
        param_xml = f'<Parameter name="context_id" value="{context_id}" />'

    farmer_ctx = get_call_context(context_id) if context_id else None
    intro_text, intro_lang = build_phone_intro(farmer_ctx)
    intro_safe = escape_twiml_say(intro_text)

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi" language="{intro_lang}">{intro_safe}</Say>
    <Connect>
        <Stream url="{ws_url}">
            {param_xml}
        </Stream>
    </Connect>
</Response>
"""
    return Response(content=twiml, media_type="text/xml; charset=utf-8")


@app.post("/twilio/status")
async def twilio_status(request: Request):
    """Handle Twilio status callbacks to keep call stats accurate"""
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    call_status = (form_data.get("CallStatus") or "").lower()
    direction = (form_data.get("Direction") or "outbound").lower()
    from_number = form_data.get("From") or "unknown"
    to_number = form_data.get("To") or PHONE_NO
    status_event = form_data.get("StatusCallbackEvent")

    logger.info(
        "📊 Status callback",
        extra={
            "call_sid": call_sid,
            "status": call_status,
            "event": status_event,
            "direction": direction,
            "from": from_number,
            "to": to_number,
        },
    )

    status_map = {
        "initiated": "queued",
        "queued": "queued",
        "ringing": "ringing",
        "answered": "in-progress",
        "in-progress": "in-progress",
        "completed": "completed",
        "busy": "no-answer",
        "failed": "failed",
        "no-answer": "no-answer",
        "canceled": "failed",
    }

    normalized_status = status_map.get(call_status, "failed")

    if not call_sid:
        logger.warning("Status callback without CallSid: ignoring")
        return Response(content="missing CallSid", media_type="text/plain")

    with get_db() as db:
        call = call_service.get_call_by_sid(db, call_sid)

        if not call:
            call_service.create_call(
                db=db,
                call_sid=call_sid,
                direction=direction,
                from_number=from_number,
                to_number=to_number,
                status=normalized_status,
            )
        else:
            call_service.update_call_status(db, call_sid, normalized_status)

    return Response(content="ok", media_type="text/plain")


@app.post("/twilio/continue")
async def twilio_continue():
    ws_url = TUNNEL_LINK.rstrip("/").replace("https://", "wss://") + "/ws/call"
    twiml = f"""
    <Response>
        <Say>Connecting you now.</Say>
        <Connect>
            <Stream url="{ws_url}"/>
        </Connect>
    </Response>
    """
    return Response(content=twiml, media_type="application/xml")

# TwiML endpoint to transfer an active call to a human agent
@app.post("/twilio/transfer")
async def twilio_transfer():
    try:
        from twilio.twiml.voice_response import VoiceResponse
        vr = VoiceResponse()
        vr.say("Please hold while I connect you to a human agent.")
        # Use callerId so the agent sees the Twilio number
        vr.dial(HUMAN_AGENT_NUMBER, caller_id=PHONE_NO)
        return Response(content=str(vr), media_type="application/xml")
    except Exception as e:
        logger.error(f"Error building transfer TwiML: {e}")
        twiml = f"""
        <Response>
            <Say>Please hold while I connect you to a human agent.</Say>
            <Dial callerId="{PHONE_NO}">{HUMAN_AGENT_NUMBER}</Dial>
        </Response>
        """
        return Response(content=twiml, media_type="application/xml")

# Manual API to trigger transfer for a specific call SID (for testing)
@app.post("/api/v1/transfer/{call_sid}")
async def api_transfer_call(call_sid: str):
    try:
        transfer_url = f"{TUNNEL_LINK.rstrip('/')}/twilio/transfer"
        # Mark status in DB
        with get_db() as db:
            call_service.update_call_status(db, call_sid, "transferring")
        # Redirect call
        await asyncio.to_thread(
            twilio_client.calls(call_sid).update,
            url=transfer_url,
            method="POST"
        )
        return JSONResponse({"success": True, "message": "Transfer initiated", "call_sid": call_sid})
    except Exception as e:
        logger.error(f"Manual transfer failed: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.websocket("/ws/call")
async def call_stream(ws: WebSocket):
    await ws.accept()
    logger.info("🎧 Media stream connected")
    
    stream_sid = None
    call_sid = None
    voice_session = None
    audio_recorder = None
    media_chunk_count = 0
    
    try:
        while True:
            message = await ws.receive_text()
            data = json.loads(message)
            event = data.get("event")

            if event == "start":
                stream_sid = data["start"]["streamSid"]
                call_sid = data["start"].get("callSid")
                logger.info(f"▶ Stream started: {stream_sid} (Call: {call_sid})")
                
                # Update call status and link stream_sid
                if call_sid:
                    with get_db() as db:
                        call_service.update_call_status(
                            db=db,
                            call_sid=call_sid,
                            status="in-progress",
                            stream_sid=stream_sid
                        )
                    
                    # Start audio recording (opt-in: RECORD_CALL_AUDIO=1)
                    if RECORD_CALL_AUDIO:
                        recording_path = call_service.get_recording_path(call_sid)
                        audio_recorder = AudioRecorder(recording_path, sample_rate=8000)
                        audio_recorder.start()
                        logger.info(f"🔴 Recording started: {recording_path}")
                
                # Farmer context from KrishiMitra call (query param -> Stream customParameters)
                custom = (data.get("start") or {}).get("customParameters") or {}
                context_id = custom.get("context_id") or ""
                farmer_ctx = pop_call_context(context_id) if context_id else None
                system_instruction = (
                    build_system_instruction(farmer_ctx) if farmer_ctx else AGENT_PERSONA
                )
                if farmer_ctx:
                    logger.info(
                        "KrishiMitra context loaded for %s (%s, %s)",
                        farmer_ctx.get("farmer_name"),
                        farmer_ctx.get("district"),
                        farmer_ctx.get("crop") or farmer_ctx.get("crops"),
                    )

                # Initialize Voice Session based on configuration
                if VOICE_ENGINE == "pipeline":
                    logger.info("🚀 Using STT -> LLM -> TTS Pipeline")
                    voice_session = VoicePipeline(
                        api_key=GEMINI_API_KEY,
                        system_instruction=system_instruction,
                    )
                else:
                    logger.info("🚀 Using Gemini Live Multimodal Session")
                    voice_session = GeminiLiveSession(
                        api_key=GEMINI_API_KEY,
                        system_instruction=system_instruction,
                    )

                
                # Set callback to send AI's audio back to Twilio
                mark_counter = 0
                async def send_audio_to_twilio(audio_data: bytes):
                    nonlocal mark_counter
                    try:
                        # Determine input sample rate based on engine
                        # Gemini Live is 24kHz, Pipeline (Google TTS) is also 24kHz in our config
                        input_rate = 24000
                        
                        logger.debug(f"🎵 AI audio: {len(audio_data)} bytes (PCM {input_rate}Hz)")
                        
                        # Step 1: Resample from AI rate to 8kHz (Twilio rate)
                        resampled = resample_audio(audio_data, input_rate, 8000, 2)
                        
                        # Record AI's audio (outgoing to caller)
                        if audio_recorder and audio_recorder.is_recording:
                            audio_recorder.write_audio(resampled)
                        
                        # Step 2: Convert PCM to μ-law
                        mulaw_data = convert_pcm16_to_mulaw(resampled)
                        
                        # Step 3: Chunk into 20ms packets (160 bytes at 8kHz µ-law)
                        # Twilio expects real-time paced audio, not bursts
                        chunk_size = 160  # 20ms of 8kHz µ-law audio
                        for i in range(0, len(mulaw_data), chunk_size):
                            chunk = mulaw_data[i:i+chunk_size]
                            audio_b64 = base64.b64encode(chunk).decode('utf-8')
                            
                            media_message = {
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {
                                    "payload": audio_b64
                                }
                            }
                            await ws.send_text(json.dumps(media_message))
                            
                            # Small delay to simulate real-time (20ms chunks)
                            await asyncio.sleep(0.02)
                        
                        logger.info(f"Sent {len(mulaw_data)} µ-law bytes in {len(mulaw_data)//chunk_size} chunks")
                    except Exception as e:
                        logger.error(f"Error sending audio to Twilio: {e}", exc_info=True)
                
                # Callback to store assistant transcript
                async def save_assistant_transcript(text: str):
                    try:
                        logger.info(f"💬 Assistant: {text}")
                        if call_sid:
                            with get_db() as db:
                                call_service.add_transcript_entry(db, call_sid, "assistant", text)
                    except Exception as e:
                        logger.error(f"Error in assistant transcript callback: {e}", exc_info=True)

                # Callback to store user transcript and detect transfer intent
                async def save_user_transcript(text: str):
                    try:
                        logger.info(f"🗣️ User: {text}")
                        if call_sid:
                            with get_db() as db:
                                call_service.add_transcript_entry(db, call_sid, "user", text)

                            # Detect if user asks for transfer
                            if detect_transfer_intent(text):
                                logger.warning(f"🔄 Transfer intent detected in user speech: '{text}'")
                                await initiate_transfer(call_sid, stream_sid)
                    except Exception as e:
                        logger.error(f"Error in user transcript callback: {e}", exc_info=True)
                
                voice_session.set_audio_callback(send_audio_to_twilio)
                voice_session.set_text_callback(save_assistant_transcript)
                if hasattr(voice_session, "set_user_transcript_callback"):
                    voice_session.set_user_transcript_callback(save_user_transcript)

                
                # Connect to Voice Session
                await voice_session.connect()
                gemini_sessions[stream_sid] = voice_session
                
                logger.info("AI is ready to talk!")

            elif event == "media":
                # Receive audio from Twilio and send to AI
                audio_b64 = data["media"]["payload"]
                mulaw_bytes = base64.b64decode(audio_b64)
                media_chunk_count += 1
                
                # Record incoming audio (µ-law from caller)
                if audio_recorder and audio_recorder.is_recording:
                    # Convert µ-law to PCM for recording
                    pcm_for_recording = convert_mulaw_to_pcm16(mulaw_bytes)
                    audio_recorder.write_audio(pcm_for_recording)
                
                # Convert μ-law 8kHz to PCM 16kHz for AI
                pcm_bytes = convert_mulaw_to_pcm16(mulaw_bytes)
                pcm_16khz = resample_audio(pcm_bytes, 8000, 16000, 2)

                if media_chunk_count % 50 == 0:
                    try:
                        import audioop
                        rms = audioop.rms(pcm_bytes, 2)
                    except Exception:
                        rms = "n/a"
                    logger.info(
                        "Incoming audio chunks: %s (mulaw %s bytes, rms %s)",
                        media_chunk_count,
                        len(mulaw_bytes),
                        rms,
                    )
                
                # Check if session is still connected
                if voice_session and not voice_session.is_connected:
                    logger.warning("⚠️ Voice session lost - attempting reconnection...")
                    try:
                        await voice_session.connect()
                        logger.info("✅ Voice session reconnected")
                    except Exception as e:
                        logger.error(f"❌ Failed to reconnect Voice Session: {e}")
                
                if voice_session and voice_session.is_connected:
                    try:
                        await voice_session.send_audio_chunk(pcm_16khz, "audio/pcm")
                        logger.debug(f"📥 Sent {len(pcm_16khz)} bytes to AI")
                    except Exception as e:
                        logger.error(f"Error sending audio to AI: {e}")
                        # Mark as disconnected so we attempt reconnection on next chunk
                        voice_session.is_connected = False
            
            elif event == "mark":
                mark_name = data.get("mark", {}).get("name", "unknown")
                logger.info(f"Twilio acknowledged mark: {mark_name}")

            elif event == "stop":
                logger.info("⏹ Stream stopped")
                break
                
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        if call_sid:
            with get_db() as db:
                call_service.update_call_status(db, call_sid, "failed", error_message=str(e))
    finally:
        # Stop audio recording (only if started)
        if audio_recorder:
            duration = audio_recorder.stop()
            logger.info(f"⏹ Recording stopped. Duration: {duration:.2f}s")
            if RECORD_CALL_AUDIO and call_sid and audio_recorder.filepath:
                with get_db() as db:
                    call_service.set_recording_path(db, call_sid, audio_recorder.filepath, duration)
        
        # Update call status to completed
        if call_sid:
            with get_db() as db:
                call_service.update_call_status(db, call_sid, "completed")
        
        # Cleanup session
        if stream_sid and stream_sid in gemini_sessions:
            if gemini_sessions[stream_sid]:
                await gemini_sessions[stream_sid].disconnect()
            del gemini_sessions[stream_sid]
        logger.info("🔌 Connection closed")


# Manual transfer via API or forced by agent
@app.post("/api/v1/transfer/{call_sid}")
async def api_transfer_call(call_sid: str):
    """Manually trigger transfer for a specific call (for testing or agent-initiated)"""
    try:
        ok = await initiate_transfer(call_sid)
        return JSONResponse({
            "success": ok,
            "message": "Transfer initiated" if ok else "Transfer failed",
            "call_sid": call_sid
        })
    except Exception as e:
        logger.error(f"Manual transfer failed: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})