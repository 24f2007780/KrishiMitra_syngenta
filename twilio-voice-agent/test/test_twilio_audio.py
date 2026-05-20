"""
Test sending audio directly to Twilio without Gemini
This will help isolate whether the issue is with Gemini or the Twilio pipeline
Run from repo root: python test/test_twilio_audio.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import asyncio
import base64
import json
import math
import struct
from gemini_ai import convert_pcm16_to_mulaw

# Generate a 1-second 440Hz sine wave (A note) at 8kHz PCM
def generate_test_tone(frequency=440, duration=1.0, sample_rate=8000):
    """Generate a sine wave tone"""
    samples = int(sample_rate * duration)
    pcm_data = b''
    for i in range(samples):
        # Generate sine wave
        value = int(16384 * math.sin(2 * math.pi * frequency * i / sample_rate))
        pcm_data += struct.pack('<h', value)  # 16-bit little-endian
    return pcm_data

# Generate test audio
print("Generating 440Hz test tone (1 second at 8kHz)...")
pcm_8khz = generate_test_tone()
print(f"PCM data: {len(pcm_8khz)} bytes")

# Convert to µ-law
mulaw_data = convert_pcm16_to_mulaw(pcm_8khz)
print(f"µ-law data: {len(mulaw_data)} bytes")

# Encode to base64 (what we'd send to Twilio)
audio_b64 = base64.b64encode(mulaw_data).decode('utf-8')
print(f"Base64 length: {len(audio_b64)} chars")

# Chunk it (Twilio expects ~20ms chunks = 160 bytes at 8kHz µ-law)
chunk_size = 160  # 20ms of 8kHz µ-law audio
chunks = [mulaw_data[i:i+chunk_size] for i in range(0, len(mulaw_data), chunk_size)]
print(f"\nWould send {len(chunks)} chunks of ~{chunk_size} bytes each")
print(f"First chunk size: {len(chunks[0])} bytes")
print(f"Last chunk size: {len(chunks[-1])} bytes")

print("\n✅ Test tone generated successfully")
print("To use this in your app, send each chunk as a separate media message")
print("with 20ms delay between chunks to match real-time playback")
