import asyncio
import logging
import os
import base64
import json
from typing import Optional, Callable
from google import genai
from google.cloud import speech
from google.cloud import texttospeech
import elevenlabs
from elevenlabs.client import ElevenLabs
from sarvamai import AsyncSarvamAI

logger = logging.getLogger(__name__)

def _clean_for_voice(text: str) -> str:
    """
    Make LLM output sound natural in TTS:
    - remove markdown bullets/asterisks
    - collapse whitespace
    - keep it concise for voice
    """
    if not text:
        return ""
    s = text.strip()
    # Remove common markdown list prefixes at line start.
    lines = []
    for line in s.splitlines():
        ln = line.strip()
        if ln.startswith(("* ", "- ", "• ")):
            ln = ln[2:].lstrip()
        # Remove numbered list like "1. " / "2) "
        if len(ln) >= 3 and ln[0].isdigit() and (ln[1:3] in (". ", ") ")):
            ln = ln[3:].lstrip()
        lines.append(ln)
    s = " ".join([x for x in lines if x])
    # Remove leftover markdown emphasis/backticks.
    for ch in ("*", "`", "_"):
        s = s.replace(ch, "")
    # Normalize whitespace.
    s = " ".join(s.split())
    return s

def _is_retryable_llm_error(err: Exception) -> bool:
    msg = str(err).lower()
    # google-genai bubbles transient overloads as 503/UNAVAILABLE in the message payload
    if "503" in msg or "unavailable" in msg or "high demand" in msg:
        return True
    if "timeout" in msg or "temporar" in msg or "rate limit" in msg:
        return True
    return False

class VoicePipeline:
    """
    Handles STT -> LLM -> TTS pipeline as an alternative to Gemini Live
    """
    
    def __init__(self, api_key: str, system_instruction: Optional[str] = None):
        self.api_key = (api_key or "").strip()
        if not self.api_key:
            raise ValueError("Gemini API key is missing or empty.")
        self.client = genai.Client(api_key=self.api_key)
        self.system_instruction = system_instruction or "You are a helpful assistant."
        
        # Providers from environment
        self.stt_provider = os.getenv("STT_PROVIDER", "sarvam")  # sarvam (default), google
        self.tts_provider = os.getenv("TTS_PROVIDER", "sarvam")  # sarvam (default), google, elevenlabs
        self.llm_model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
        self.sarvam_api_key = os.getenv("SARVAM_API_KEY")
        self.sarvam_model = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")
        self.sarvam_voice = os.getenv("SARVAM_VOICE", "shubh")
        self.sarvam_language = os.getenv("SARVAM_LANGUAGE", "en-IN")
        self.sarvam_pace = float(os.getenv("SARVAM_PACE", "1.0"))
        self.sarvam_stt_model = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
        self.sarvam_stt_language = os.getenv("SARVAM_STT_LANGUAGE", self.sarvam_language)
        # NOTE: downstream Twilio bridge (app.py) hardcodes input_rate=24000 for
        # whatever the active TTS provider returns, so this must stay 24000
        # unless that resampling assumption is updated too.
        self.sarvam_sample_rate = int(os.getenv("SARVAM_SAMPLE_RATE", "24000"))
        
        # Callbacks
        self.on_audio_response: Optional[Callable] = None
        self.on_text_response: Optional[Callable] = None
        self.on_user_transcript: Optional[Callable] = None
        
        self.is_connected = False
        self.audio_input_queue = asyncio.Queue()
        self.stt_task = None
        self._audio_chunks_received = 0
        self._last_interim = ""
        self._conversation = []
        self._max_turns = 6
        self._last_clarification_ts = 0.0
        self._last_error_notice_ts = 0.0
        self._last_assistant_text = ""
        
        # Initialize provider clients
        if self.stt_provider == "google":
            self.speech_client = speech.SpeechAsyncClient()

        if self.tts_provider == "google":
            self.tts_client = texttospeech.TextToSpeechAsyncClient()
        elif self.tts_provider == "elevenlabs":
            self.el_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

        if self.stt_provider == "sarvam" or self.tts_provider == "sarvam":
            if not self.sarvam_api_key:
                raise ValueError("SARVAM_API_KEY is required when STT_PROVIDER=sarvam or TTS_PROVIDER=sarvam")
            self.sarvam_client = AsyncSarvamAI(api_subscription_key=self.sarvam_api_key)

    async def connect(self):
        """Initialize the pipeline"""
        self.is_connected = True
        self.stt_task = asyncio.create_task(self._run_stt_loop())
        logger.info(f"Pipeline connected (STT: {self.stt_provider}, TTS: {self.tts_provider})")

    async def disconnect(self):
        """Shutdown the pipeline"""
        self.is_connected = False
        if self.stt_task:
            self.stt_task.cancel()
        logger.info("Pipeline disconnected")

    async def send_audio_chunk(self, audio_data: bytes, mime_type: str = "audio/pcm"):
        """Receive audio from Twilio and put into STT queue"""
        if self.is_connected:
            self._audio_chunks_received += 1
            if self._audio_chunks_received % 50 == 0:
                logger.info(
                    "STT audio chunks received: %s (last chunk %s bytes)",
                    self._audio_chunks_received,
                    len(audio_data),
                )
            await self.audio_input_queue.put(audio_data)

    async def _run_stt_loop(self):
        """Continuous STT loop"""
        if self.stt_provider == "google":
            await self._run_google_stt()
        elif self.stt_provider == "sarvam":
            await self._run_sarvam_stt()

    async def _run_google_stt(self):
        """Google Cloud Streaming STT implementation"""
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US", # Should be configurable
            enable_automatic_punctuation=True,
            model="telephony",
            use_enhanced=True,
        )
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
            single_utterance=False,
            enable_voice_activity_events=True,
        )

        try:
            # The first request must contain the streaming_config
            first_request = speech.StreamingRecognizeRequest(streaming_config=streaming_config)

            async def request_generator():
                yield first_request
                while self.is_connected:
                    chunk = await self.audio_input_queue.get()
                    yield speech.StreamingRecognizeRequest(audio_content=chunk)

            responses = await self.speech_client.streaming_recognize(
                requests=request_generator()
            )

            async for response in responses:
                if response.speech_event_type:
                    logger.debug("STT event: %s", response.speech_event_type.name)
                if not response.results:
                    continue
                
                result = response.results[0]
                if not result.alternatives:
                    continue
                
                transcript = result.alternatives[0].transcript or ""
                cleaned = transcript.strip()

                if result.is_final:
                    if not cleaned:
                        continue
                    logger.info("STT Final: %s", cleaned)
                    if self.on_user_transcript:
                        await self.on_user_transcript(cleaned)
                    await self._process_text_with_llm(cleaned)
                    self._last_interim = ""
                else:
                    if cleaned and cleaned != self._last_interim:
                        self._last_interim = cleaned
                        logger.debug("STT Interim: %s", cleaned)
        except Exception as e:
            if self.is_connected:
                logger.error(f"Google STT Error: {e}")

    async def _run_sarvam_stt(self):
        """Sarvam streaming STT implementation.

        Twilio audio arrives as raw PCM16 at 16kHz (app.py resamples the
        inbound mulaw before calling send_audio_chunk), so the connection is
        opened with input_audio_codec=pcm_s16le / sample_rate=16000 to match
        exactly — no WAV wrapping needed per chunk.
        """
        if not self.sarvam_api_key:
            logger.error("Sarvam STT Error: SARVAM_API_KEY is not set")
            return

        try:
            async with self.sarvam_client.speech_to_text_streaming.connect(
                language_code=self.sarvam_stt_language,
                model=self.sarvam_stt_model,
                sample_rate="16000",
                input_audio_codec="pcm_s16le",
            ) as ws:
                async def sender():
                    try:
                        while self.is_connected:
                            chunk = await self.audio_input_queue.get()
                            await ws.transcribe(
                                audio=base64.b64encode(chunk).decode("ascii"),
                                sample_rate=16000,
                            )
                    except asyncio.CancelledError:
                        pass

                send_task = asyncio.create_task(sender())
                try:
                    async for message in ws:
                        if message.type == "error":
                            logger.error("Sarvam STT error event: %s", message.data)
                            continue
                        if message.type != "data":
                            continue
                        transcript = getattr(message.data, "transcript", "") or ""
                        cleaned = transcript.strip()
                        if not cleaned:
                            continue
                        logger.info("STT Final (sarvam): %s", cleaned)
                        if self.on_user_transcript:
                            await self.on_user_transcript(cleaned)
                        await self._process_text_with_llm(cleaned)
                finally:
                    send_task.cancel()
        except Exception as e:
            if self.is_connected:
                logger.error(f"Sarvam STT Error: {e}")

    async def _process_text_with_llm(self, text: str):
        """Send transcript to Gemini LLM"""
        try:
            # If the user input is too short, ask a clarifying question directly
            if len(text.split()) < 3:
                clarification = (
                    "Thanks for sharing. Could you please tell me a bit more about what you need help with? "
                    "For example: courses, enrollment, payments, or technical issues."
                )
                now = asyncio.get_event_loop().time()
                if (
                    self._last_assistant_text == clarification
                    and (now - self._last_clarification_ts) < 8
                ):
                    logger.info("Short input detected; skipping repeated clarification.")
                    return
                logger.info("Short input detected, asking clarification.")
                if self.on_text_response:
                    await self.on_text_response(clarification)
                await self._generate_tts(clarification)
                self._append_history("user", text)
                self._append_history("assistant", clarification)
                self._last_assistant_text = clarification
                self._last_clarification_ts = now
                return

            logger.info(f"Sending to LLM: {text}")
            contents = self._conversation + [
                {"role": "user", "parts": [{"text": text}]}
            ]
            logger.debug("LLM history turns: %s", len(self._conversation))

            # Retry on transient model overloads (503 / UNAVAILABLE).
            # Keep this small: in a voice call, long waits feel broken.
            response = None
            last_err: Exception | None = None
            backoffs = (0.4, 0.8, 1.6)
            for attempt in range(len(backoffs) + 1):
                try:
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.llm_model,
                        contents=contents,
                        config={"system_instruction": self.system_instruction},
                    )
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    if not _is_retryable_llm_error(e) or attempt >= len(backoffs):
                        break
                    delay = backoffs[attempt]
                    logger.warning("LLM transient error; retrying in %.1fs (%s)", delay, e)
                    await asyncio.sleep(delay)

            if response is None and last_err is not None:
                raise last_err
            
            response_text = (response.text or "").strip()
            response_voice = _clean_for_voice(response_text)
            logger.info("LLM Response: %s", response_voice)
            
            self._append_history("user", text)
            self._append_history("assistant", response_voice)
            self._last_assistant_text = response_voice

            if self.on_text_response:
                await self.on_text_response(response_voice)
            
            await self._generate_tts(response_voice)
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            now = asyncio.get_event_loop().time()
            if (now - self._last_error_notice_ts) >= 15:
                if _is_retryable_llm_error(e):
                    fallback = "Quick heads-up: the AI service is under heavy load. Please say that again in a moment."
                else:
                    fallback = "I’m having trouble connecting right now. Please give me a moment and try again."
                fallback = _clean_for_voice(fallback)
                if self.on_text_response:
                    await self.on_text_response(fallback)
                try:
                    await self._generate_tts(fallback)
                    self._last_assistant_text = fallback
                except Exception:
                    pass
                self._last_error_notice_ts = now

    async def _generate_tts(self, text: str):
        """Convert LLM text to audio"""
        try:
            if self.tts_provider == "google":
                await self._generate_google_tts(text)
            elif self.tts_provider == "elevenlabs":
                await self._generate_elevenlabs_tts(text)
            elif self.tts_provider == "sarvam":
                await self._generate_sarvam_tts(text)
        except Exception as e:
            logger.error(f"TTS Error: {e}")

    async def _generate_google_tts(self, text: str):
        input_text = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-F"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000
        )

        response = await self.tts_client.synthesize_speech(
            request={"input": input_text, "voice": voice, "audio_config": audio_config}
        )
        
        if self.on_audio_response:
            await self.on_audio_response(response.audio_content)

    async def _generate_elevenlabs_tts(self, text: str):
        # ElevenLabs is usually synchronous, wrap in thread
        audio_gen = await asyncio.to_thread(
            self.el_client.generate,
            text=text,
            voice="Rachel", # Configurable
            model="eleven_monolingual_v1"
        )
        
        # ElevenLabs returns a generator or bytes depending on usage
        audio_bytes = b"".join(list(audio_gen))
        
        if self.on_audio_response:
            await self.on_audio_response(audio_bytes)

    async def _generate_sarvam_tts(self, text: str):
        if not self.sarvam_api_key:
            raise RuntimeError("SARVAM_API_KEY is not set")

        # bulbul:v3 REST caps input at 2500 chars; truncate defensively so a
        # long LLM reply can't turn into a hard API error mid-call.
        response = await self.sarvam_client.text_to_speech.convert(
            text=text[:2500],
            language_code=self.sarvam_language,
            model=self.sarvam_model,
            speaker=self.sarvam_voice,
            pace=self.sarvam_pace,
            speech_sample_rate=self.sarvam_sample_rate,
        )

        if not response.audios:
            raise RuntimeError("Sarvam TTS response contained no audio")

        audio_bytes = base64.b64decode(response.audios[0])

        if self.on_audio_response:
            await self.on_audio_response(audio_bytes)

    def set_audio_callback(self, callback: Callable):
        self.on_audio_response = callback
    
    def set_text_callback(self, callback: Callable):
        self.on_text_response = callback

    def set_user_transcript_callback(self, callback: Callable):
        self.on_user_transcript = callback

    def _append_history(self, role: str, text: str):
        # google-genai expects roles: "user" or "model"
        normalized_role = "model" if role == "assistant" else role
        self._conversation.append({"role": normalized_role, "parts": [{"text": text}]})
        # Keep only the last N turns (user+assistant pairs)
        if len(self._conversation) > self._max_turns * 2:
            self._conversation = self._conversation[-self._max_turns * 2:]
