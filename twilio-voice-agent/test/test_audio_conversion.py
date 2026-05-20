"""Test audio conversion pipeline. Run: python test/test_audio_conversion.py"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import struct
from gemini_ai import convert_pcm16_to_mulaw, convert_mulaw_to_pcm16, resample_audio

# Create a test tone (1kHz sine wave)
import math
sample_rate = 24000
duration = 0.1  # 100ms
samples = int(sample_rate * duration)

# Generate sine wave
pcm_data = b''
for i in range(samples):
    value = int(32767 * 0.5 * math.sin(2 * math.pi * 1000 * i / sample_rate))
    pcm_data += struct.pack('<h', value)  # little-endian int16

print(f"Generated {len(pcm_data)} bytes of PCM @ 24kHz")
print(f"  = {samples} samples = {duration}s")

# Test resampling 24kHz -> 8kHz
resampled = resample_audio(pcm_data, 24000, 8000, 2)
expected_samples = int(samples * 8000 / 24000)
expected_bytes = expected_samples * 2
print(f"\nResampled to 8kHz: {len(resampled)} bytes (expected ~{expected_bytes})")

# Test PCM -> µ-law conversion
mulaw = convert_pcm16_to_mulaw(resampled)
expected_mulaw = expected_samples  # µ-law is 8-bit, PCM16 is 16-bit
print(f"Converted to µ-law: {len(mulaw)} bytes (expected ~{expected_mulaw})")

# Test reverse: µ-law -> PCM
pcm_back = convert_mulaw_to_pcm16(mulaw)
print(f"Converted back to PCM: {len(pcm_back)} bytes")

# Verify
if len(mulaw) * 2 == len(resampled):
    print("\n✅ Conversion sizes correct!")
else:
    print(f"\n❌ Size mismatch: mulaw*2={len(mulaw)*2} != resampled={len(resampled)}")

# Check if data is valid (not all zeros)
if any(b != 0 for b in mulaw[:10]):
    print("✅ µ-law data is not all zeros")
else:
    print("❌ µ-law data might be corrupted (all zeros)")
