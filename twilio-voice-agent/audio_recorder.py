"""
Audio recording utility for saving call audio
"""
import wave
import asyncio
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Records audio stream to WAV file"""
    
    def __init__(self, filepath: str, sample_rate: int = 8000, channels: int = 1):
        self.filepath = filepath
        self.sample_rate = sample_rate
        self.channels = channels
        self.wav_file: Optional[wave.Wave_write] = None
        self.is_recording = False
        self.audio_buffer = []
        
    def start(self):
        """Start recording"""
        try:
            self.wav_file = wave.open(self.filepath, 'wb')
            self.wav_file.setnchannels(self.channels)
            self.wav_file.setsampwidth(2)  # 16-bit PCM
            self.wav_file.setframerate(self.sample_rate)
            self.is_recording = True
            logger.info(f"Started recording to {self.filepath}")
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            raise
    
    def write_audio(self, audio_data: bytes):
        """Write audio chunk to file"""
        if self.is_recording and self.wav_file:
            try:
                self.wav_file.writeframes(audio_data)
            except Exception as e:
                logger.error(f"Error writing audio: {e}")
    
    def stop(self) -> float:
        """Stop recording and return duration in seconds"""
        duration = 0.0
        if self.wav_file:
            try:
                self.is_recording = False
                frames = self.wav_file.getnframes()
                duration = frames / self.sample_rate
                self.wav_file.close()
                logger.info(f"Stopped recording. Duration: {duration:.2f}s")
            except Exception as e:
                logger.error(f"Error stopping recording: {e}")
        return duration
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
