import os
import asyncio
import queue
import sounddevice as sd
import numpy as np
from google import genai
from dotenv import load_dotenv

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
# MODEL = "gemini-live-2.5-flash-native-audio"

# Audio params
SEND_SR = 16000   # capture rate for Gemini input
RECV_SR = 24000   # Gemini returns 24 kHz
CHUNK = 1024      # frames per chunk
CHANNELS = 1

async def main():
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set in environment")
    client = genai.Client(api_key=API_KEY)
    audio_out_q = queue.Queue()   # PCM 24kHz bytes from Gemini

    async def audio_callback(audio_data: bytes):
        audio_out_q.put(audio_data)

    async def recv_loop(session):
        async for turn in session.receive():
            if turn.server_content and turn.server_content.model_turn:
                for part in turn.server_content.model_turn.parts:
                    if part.inline_data and isinstance(part.inline_data.data, bytes):
                        await audio_callback(part.inline_data.data)

    async with client.aio.live.connect(
        model=MODEL,
        config={
            "response_modalities": ["AUDIO"],
            "system_instruction": "You are a concise, friendly voice assistant. Keep replies under 10 seconds."
        }
    ) as session:
        print("Connected. Speak into your mic… Ctrl+C to stop.")

        # Start receiver
        recv_task = asyncio.create_task(recv_loop(session))

        loop = asyncio.get_running_loop()

        # Sounddevice streams
        def sd_callback(indata, frames, time, status):
            if status:
                print("SD status:", status)
            pcm16 = (indata[:, 0].copy() * 32767).astype(np.int16).tobytes()
            asyncio.run_coroutine_threadsafe(
                session.send_realtime_input(audio={
                    "data": pcm16,
                    "mime_type": "audio/pcm"
                }),
                loop,
            )

        def sd_play_callback(outdata, frames, time, status):
            if status:
                print("SD play status:", status)
            try:
                chunk = audio_out_q.get_nowait()
                # chunk is 24kHz mono PCM16; sounddevice expects float32 [-1,1]
                arr = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                if len(arr) < frames:
                    padded = np.zeros(frames, dtype=np.float32)
                    padded[:len(arr)] = arr
                    outdata[:, 0] = padded
                else:
                    outdata[:, 0] = arr[:frames]
            except queue.Empty:
                outdata[:] = 0

        with sd.InputStream(channels=CHANNELS, samplerate=SEND_SR, blocksize=CHUNK, callback=sd_callback):
            with sd.OutputStream(channels=CHANNELS, samplerate=RECV_SR, blocksize=CHUNK, callback=sd_play_callback):
                try:
                    await recv_task
                except asyncio.CancelledError:
                    pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")