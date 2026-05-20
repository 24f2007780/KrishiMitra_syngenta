"""
Gemini AI Module for Live Audio Conversations
Integrates Google's Gemini Live API for real-time voice interactions
"""

import asyncio
import base64
import logging
import os
from typing import Optional, Callable
from google import genai
try:
    import websockets
except ImportError:  # websockets optional but helpful for error typing
    websockets = None

logger = logging.getLogger(__name__)

# WebSocket timeout configuration
KEEPALIVE_TIMEOUT = 30  # seconds
CONNECTION_TIMEOUT = 60  # seconds for initial connection


def _env_truthy(*names: str) -> bool:
    for n in names:
        v = (os.getenv(n) or "").strip().lower()
        if v in ("1", "true", "yes", "y", "on"):
            return True
    return False

class GeminiLiveSession:
    """
    Handles real-time audio conversations with Gemini Live API
    """
    
    def __init__(self, api_key: str, system_instruction: Optional[str] = None, tools: Optional[list] = None):
        """
        Initialize Gemini Live Session
        
        Args:
            api_key: Google Gemini API key
            system_instruction: System prompt for Gemini's behavior
            tools: List of tool definitions (dicts)
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.session_cm = None  # context manager returned by connect
        self.session = None
        self.is_connected = False
        self.receiver_task: Optional[asyncio.Task] = None
        self.sender_task: Optional[asyncio.Task] = None
        self.keepalive_task: Optional[asyncio.Task] = None
        self.last_activity_time = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        
        # Configuration
        # This class uses the GenAI Live API (client.aio.live.connect).
        # Allow switching models via env for quick experiments / previews.
        live_api_enabled = _env_truthy("LIVE_API", "live_api")
        default_model = "gemini-2.5-flash-native-audio-preview-09-2025"
        env_model = (os.getenv("LIVE_API_MODEL") or os.getenv("live_api_model") or "").strip()
        self.model = env_model if (live_api_enabled and env_model) else default_model
        self.config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": system_instruction or "You are a helpful and friendly AI assistant answering phone calls. Keep responses concise and natural for voice conversation.",
        }
        if tools:
            self.config["tools"] = tools
        
        # Audio queues
        self.audio_output_queue = asyncio.Queue()
        self.audio_input_queue = asyncio.Queue(maxsize=20)
        
        # Callbacks for multimodal responses
        self.on_audio_response: Optional[Callable] = None
        self.on_text_response: Optional[Callable] = None
        self.on_user_transcript: Optional[Callable] = None

    async def connect(self):
        """Connect to Gemini Live API"""
        try:
            logger.info("🔌 Connecting to Gemini Live API...")
            # Keep the context manager so we can call __aexit__ correctly
            self.session_cm = self.client.aio.live.connect(
                model=self.model,
                config=self.config
            )
            self.session = await asyncio.wait_for(
                self.session_cm.__aenter__(),
                timeout=CONNECTION_TIMEOUT
            )
            self.is_connected = True
            self.reconnect_attempts = 0
            self.last_activity_time = asyncio.get_event_loop().time()
            logger.info("✅ Connected to Gemini Live API")
            
            # Start receiving responses
            self.receiver_task = asyncio.create_task(self._receive_responses())
            self.sender_task = asyncio.create_task(self._send_audio())
            self.keepalive_task = asyncio.create_task(self._keepalive_monitor())
            
        except asyncio.TimeoutError:
            logger.error("❌ Connection to Gemini timed out")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to connect to Gemini: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Gemini Live API"""
        try:
            self.is_connected = False

            # Cancel background tasks
            for task in (self.receiver_task, self.sender_task, self.keepalive_task):
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            if self.session_cm:
                try:
                    await self.session_cm.__aexit__(None, None, None)
                except AttributeError:
                    # Fallback if __aexit__ not present
                    if self.session and hasattr(self.session, "close"):
                        await self.session.close()
                logger.info("👋 Disconnected from Gemini Live API")
            self.session_cm = None
            self.session = None
            self.receiver_task = None
            self.sender_task = None
            self.keepalive_task = None
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    async def send_audio_chunk(self, audio_data: bytes, mime_type: str = "audio/pcm"):
        """
        Send audio chunk to Gemini
        
        Args:
            audio_data: Raw audio bytes (mulaw will be converted to PCM)
            mime_type: Audio format (default: audio/pcm)
        """
        try:
            await self.audio_input_queue.put({
                "data": audio_data,
                "mime_type": mime_type
            })
        except Exception as e:
            logger.error(f"Error queuing audio: {e}")
    
    async def _send_audio(self):
        """Internal: Send audio from queue to Gemini"""
        while self.is_connected:
            try:
                audio_msg = await self.audio_input_queue.get()
                if self.session:
                    await self.session.send_realtime_input(audio=audio_msg)
                    self.last_activity_time = asyncio.get_event_loop().time()
            except Exception as e:
                # Handle normal close
                close_ok = False
                if websockets:
                    from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
                    close_ok = isinstance(e, (ConnectionClosedOK, ConnectionClosedError)) or "code = 1000" in str(e)
                else:
                    close_ok = "code = 1000" in str(e)

                if close_ok:
                    logger.debug("Send loop: Gemini connection closed")
                    break

                logger.error(f"Error sending audio to Gemini: {e}")
                # Check if it's a keepalive timeout and attempt reconnect
                if "keepalive ping timeout" in str(e) or "1011" in str(e):
                    logger.warning("⚠️ Keepalive ping timeout detected - connection lost")
                    self.is_connected = False
                    break
                    
                if not self.is_connected:
                    break
    
    async def _receive_responses(self):
        """Internal: Receive responses from Gemini with improved error handling"""
        while self.is_connected:
            try:
                if not self.session:
                    break
                    
                turn = self.session.receive()
                async for response in turn:
                    try:
                        self.last_activity_time = asyncio.get_event_loop().time()
                        server_content = getattr(response, 'server_content', None)
                        if not server_content:
                            continue
                            
                        model_turn = getattr(server_content, 'model_turn', None)
                        if not model_turn:
                            continue
                            
                        parts = getattr(model_turn, 'parts', None)
                        if not parts:
                            continue
                            
                        for part in parts:
                            # Handle audio data
                            inline_data = getattr(part, 'inline_data', None)
                            if inline_data:
                                audio_data = getattr(inline_data, 'data', None)
                                if audio_data and isinstance(audio_data, bytes):
                                    logger.info(f"🎵 Received audio from Gemini: {len(audio_data)} bytes")
                                    await self.audio_output_queue.put(audio_data)
                                    if self.on_audio_response:
                                        await self.on_audio_response(audio_data)
                            
                            # Handle text data (for transcripts/transfer detection)
                            text = getattr(part, 'text', None)
                            if text and isinstance(text, str):
                                logger.info(f"💬 Gemini text: {text}")
                                if self.on_text_response:
                                    await self.on_text_response(text)
                    except AttributeError:
                        pass
                    except Exception as e:
                        logger.debug(f"Response processing: {e}")
                
            except Exception as e:
                # Handle normal close (code 1000) without spamming errors
                close_ok = False
                error_str = str(e)
                
                if websockets:
                    from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
                    close_ok = isinstance(e, (ConnectionClosedOK, ConnectionClosedError)) or "code = 1000" in error_str
                else:
                    close_ok = "code = 1000" in error_str

                if close_ok:
                    logger.debug("Gemini connection closed normally (1000)")
                    break
                
                # Check for keepalive timeout or internal errors
                if "keepalive ping timeout" in error_str or "1011" in error_str or "internal error" in error_str:
                    logger.warning(f"⚠️ Gemini connection error (keepalive/timeout): {e}")
                    self.is_connected = False
                    break
                
                logger.error(f"Error receiving from Gemini: {e}")
                if not self.is_connected:
                    break
    
    async def _keepalive_monitor(self):
        """Monitor connection health and detect stale connections"""
        while self.is_connected:
            try:
                await asyncio.sleep(KEEPALIVE_TIMEOUT)
                
                if not self.is_connected or not self.last_activity_time:
                    break
                
                current_time = asyncio.get_event_loop().time()
                time_since_activity = current_time - self.last_activity_time
                
                # If no activity for 2x timeout period, connection is likely dead
                if time_since_activity > (KEEPALIVE_TIMEOUT * 2):
                    logger.warning(f"⚠️ No activity for {time_since_activity:.1f}s - marking connection as stale")
                    self.is_connected = False
                    break
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Keepalive monitor error: {e}")
    
    async def get_audio_response(self) -> Optional[bytes]:
        """
        Get audio response from Gemini (blocking until available)
        
        Returns:
            Audio bytes in PCM format (24kHz)
        """
        try:
            return await self.audio_output_queue.get()
        except Exception as e:
            logger.error(f"Error getting audio response: {e}")
            return None
    
    def set_audio_callback(self, callback: Callable):
        """Set callback for when audio response is received"""
        self.on_audio_response = callback
    
    def set_text_callback(self, callback: Callable):
        """Set callback for when text response is received"""
        self.on_text_response = callback
    
    def set_user_transcript_callback(self, callback: Callable):
        """Set callback for when user speech is transcribed"""
        self.on_user_transcript = callback


def convert_mulaw_to_pcm16(mulaw_data: bytes) -> bytes:
    """
    Convert μ-law audio to 16-bit PCM
    Twilio sends audio in μ-law format, Gemini expects PCM
    
    Args:
        mulaw_data: μ-law encoded audio bytes
        
    Returns:
        PCM 16-bit audio bytes
    """
    import audioop
    try:
        # Convert μ-law (8-bit) to linear PCM (16-bit)
        pcm_data = audioop.ulaw2lin(mulaw_data, 2)  # 2 = 16-bit samples
        return pcm_data
    except Exception as e:
        logger.error(f"Error converting μ-law to PCM: {e}")
        return b''


def convert_pcm16_to_mulaw(pcm_data: bytes) -> bytes:
    """
    Convert 16-bit PCM to μ-law audio
    Gemini sends PCM, Twilio expects μ-law
    
    Args:
        pcm_data: 16-bit PCM audio bytes
        
    Returns:
        μ-law encoded audio bytes
    """
    import audioop
    try:
        # Convert linear PCM (16-bit) to μ-law (8-bit)
        mulaw_data = audioop.lin2ulaw(pcm_data, 2)  # 2 = 16-bit samples
        return mulaw_data
    except Exception as e:
        logger.error(f"Error converting PCM to μ-law: {e}")
        return b''


def resample_audio(audio_data: bytes, from_rate: int, to_rate: int, sample_width: int = 2) -> bytes:
    """
    Resample audio from one sample rate to another
    
    Args:
        audio_data: Audio bytes
        from_rate: Source sample rate (Hz)
        to_rate: Target sample rate (Hz)
        sample_width: Bytes per sample (2 for 16-bit)
        
    Returns:
        Resampled audio bytes
    """
    import audioop
    try:
        # Resample audio
        resampled, _ = audioop.ratecv(
            audio_data,
            sample_width,
            1,  # mono
            from_rate,
            to_rate,
            None
        )
        return resampled
    except Exception as e:
        logger.error(f"Error resampling audio: {e}")
        return audio_data
