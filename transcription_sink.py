import asyncio
import io
import discord
import speech_recognition as sr
from discord.ext import voice_recv
import wave
from pydub import AudioSegment
from pydub.playback import play
import numpy as np
from pydub.silence import detect_nonsilent

def _debug_pcm_data(pcm_data):
    """Analyze the raw PCM data before converting it to WAV."""
    np_audio = np.frombuffer(pcm_data, dtype=np.int16)

    print(f"PCM Data Debugging:")
    print(f"- Length of PCM Data: {len(pcm_data)} bytes")
    print(f"- First 100 Samples: {np_audio[:100]}")
    print(f"- Min Sample Value: {np.min(np_audio)}, Max Sample Value: {np.max(np_audio)}")

class TranscriptionSink(voice_recv.AudioSink):
    def __init__(self, bot, on_silent_callback):
        super().__init__()
        self.bot = bot  # Store bot reference
        self.audio_buffer = io.BytesIO()
        self.recognizer = sr.Recognizer()
        self.speaking_users = set()
        self.silence_timer = None
        self.on_silent_callback = on_silent_callback  # Assign event callback

    def wants_opus(self) -> bool:
        return False  # Request PCM for STT

    def write(self, user: discord.Member | None, data: voice_recv.VoiceData):
        """Called when receiving audio packets"""
        if user:
            self.speaking_users.add(user.id)
            self.audio_buffer.write(data.pcm)

        # Reset silence timer
        if self.silence_timer:
            self.silence_timer.cancel()

        # Ensure we use the bot's main event loop
        loop = self.bot.loop  

        # Schedule silence detection
        self.silence_timer = loop.call_later(1, self._on_silent_detected)

    def _on_silent_detected(self):
        """Triggered when no audio has been received for X seconds."""
        print("Silence detected, processing transcription...")

        if self.audio_buffer.getbuffer().nbytes == 0:
            print("No audio data recorded, skipping transcription.")
            return

        # Convert raw PCM buffer to WAV format
        wav_buffer = self._convert_pcm_to_wav(self.audio_buffer.getvalue())

        # Save for debugging
        with open("debug_fixed.wav", "wb") as f:
            f.write(wav_buffer.getvalue())

        # play(AudioSegment.from_wav(wav_buffer))  # Play the audio for debugging

        # Perform speech-to-text transcription
        with sr.AudioFile(wav_buffer) as source:
            audio_data = self.recognizer.record(source)

        try:
            text = self.recognizer.recognize_google(audio_data)
            print(f"Transcription: {text}")

            if self.on_silent_callback:
                asyncio.run_coroutine_threadsafe(self.on_silent_callback(text), self.bot.loop)

        except sr.UnknownValueError:
            print("Could not understand the audio.")
        except sr.RequestError:
            print("Error connecting to the recognition service.")

        self.audio_buffer = io.BytesIO()  # Reset buffer

    def _convert_pcm_to_wav(self, pcm_data):
        """Converts raw PCM data to a valid WAV file buffer."""
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono audio
            wav_file.setsampwidth(2)  # 16-bit samples
            wav_file.setframerate(96000)  # 96 kHz sample rate
            wav_file.writeframes(pcm_data)

        # resample to 44.1 kHz
        wav_buffer.seek(0)
        audio = AudioSegment.from_wav(wav_buffer)
        audio = audio.set_frame_rate(44100)
        audio.export(wav_buffer, format="wav")

        wav_buffer.seek(0)  # Reset buffer position
        return wav_buffer

    def cleanup(self):
        """Called when the sink is stopped."""
        print("Cleaning up TranscriptionSink.")
        self.audio_buffer.close()
