import discord
import speech_recognition as sr
import asyncio
import tempfile
import numpy as np
from pydub import AudioSegment
from collections import deque
import time
import re

class DiscordAudioSink(discord.sinks.WaveSink):
    """Custom AudioSink to capture audio from Discord voice channel, detect silence, and track conversations."""

    def __init__(self, chatbot_instance, vc, bot, on_silence=None, silence_threshold=-40.0, silence_duration=5):
        """
        :param chatbot_instance: AI chatbot instance for responses
        :param vc: Voice channel connection
        :param silence_threshold: Volume level (in dB) below which we consider silence
        :param silence_duration: Time (in seconds) of continuous silence before firing an event
        """
        self.chatbot = chatbot_instance
        self.vc = vc
        self.bot = bot
        self.recognizer = sr.Recognizer()
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.audio_buffer = bytearray()  # Store raw audio data
        self.audio_queue = deque(maxlen=10)  # Store last few audio chunks
        self.text_buffer = ""  # Store accumulated transcribed text
        self.last_sound_time = time.time()

        # Callbacks
        self.on_silence = on_silence

    def write(self, data):
        """Collects raw audio data and detects silence without converting immediately."""
        try:
            # Append raw PCM data to buffer
            self.audio_buffer.extend(data)

            # Analyze volume level
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
                temp_wav.write(data)
                temp_wav.close()
                audio_segment = AudioSegment.from_wav(temp_wav.name)
                volume = audio_segment.dBFS  # Get volume in decibels

            # Check for silence
            if volume < self.silence_threshold:
                if time.time() - self.last_sound_time > self.silence_duration:
                    print("Silence detected! Processing full audio buffer...")
                    self.process_audio_buffer()  # Convert the full accumulated buffer to text
                    self.audio_buffer.clear()  # Reset buffer
            else:
                self.last_sound_time = time.time()  # Reset silence timer

        except Exception as e:
            print(f"Audio processing error: {e}")

    def process_audio_buffer(self):
        """Converts the accumulated audio buffer to text when silence is detected."""
        if not self.audio_buffer:
            return

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
                temp_wav.write(self.audio_buffer)
                temp_wav.close()

                # Convert full audio buffer to text
                with sr.AudioFile(temp_wav.name) as source:
                    audio = self.recognizer.record(source)

                text = self.recognizer.recognize_google(audio)
                print(f"Processed Text: {text}")

                # Fire event with full transcribed text
                if self.on_silence:
                    asyncio.run_coroutine_threadsafe(self.on_text(text.strip(), self.vc), self.bot.loop)

        except Exception as e:
            print(f"Error processing audio buffer: {e}")
