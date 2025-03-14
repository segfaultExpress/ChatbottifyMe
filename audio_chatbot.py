import os
from elevenlabs import play
from elevenlabs.client import ElevenLabs
from chatbot import Chatbot
from config import VOICE_ID
import speech_recognition as sr
import argparse
import tempfile
from pydub import AudioSegment
import discord

# Load API Keys
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise ValueError("Missing API key! Set the ELEVENLABS_API_KEY environment variable.")

class AudioChatbot(Chatbot):
    """Extends Chatbot to include audio processing methods."""
    def __init__(self, conversation_limit=5):
        super().__init__(conversation_limit=conversation_limit)
        self.el_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    def respond_with_context(self, input_text, callback=None):
        """Generates a response and speaks it using TTS."""
        response_text = super().respond_with_context(input_text)
        print(f"Chatbot: {response_text}")
        self._text_to_speech(response_text, callback)
        return response_text

    def set_vc(self, vc):
        self.vc = vc

    def _text_to_speech(self, text, callback=None):
        """Converts text to speech and plays it using ElevenLabs."""
        print(f"Converting text to speech: {text}")
        try:
            audio = b"".join(self.el_client.text_to_speech.convert(
                text=text,
                voice_id=VOICE_ID,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
            ))
        except Exception as e:
            print(f"Error converting text to speech: {e}")
            return

        print("Text to speech conversion complete.")
        
        try:
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_mp3:


                try:
                    temp_mp3.write(audio)
                except Exception as e:
                    print(f"Error saving audio: {e}")

                try:
                    temp_mp3.close()

                    # Convert to WAV format
                    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                    sound = AudioSegment.from_mp3(temp_mp3.name)
                    sound.export(temp_wav.name, format="wav")
                    temp_wav.close()
                except Exception as e:
                    print(f"Error converting audio: {e}")
                    return

            self.vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=temp_wav.name), after=callback)
            print("Playing audio...")
        except Exception as e:
            print(f"Error converting audio: {e}")

    def converse_vocally(self):
        """Starts a fully vocal conversation using the microphone."""
        self.mic = sr.Microphone()
        self.recognizer = sr.Recognizer()
        
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            print("Listening for speech... (speak and pause for ~0.5s to process)")

            while True:
                try:
                    # Listen for audio until silence is detected
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=10)
                    
                    # Convert speech to text
                    text = self.recognizer.recognize_google(audio)
                    print(f"You: {text}")

                    # Pass recognized text to chatbot
                    self.respond_with_context(text)

                except sr.UnknownValueError:
                    print("Sorry, I didn't catch that. Try speaking again.")
                except sr.RequestError as e:
                    print(f"Speech recognition service error: {e}")
                except KeyboardInterrupt:
                    print("Conversation ended.")
                    break

if __name__ == "__main__":
    chatbot = AudioChatbot()
    # chatbot.converse()  # Text + speech mode
    # chatbot.converse_vocally()  # Full voice mode

    parser = argparse.ArgumentParser(description="Chatbot with audio processing.")

    parser.add_argument(
        "--text",
        type=str,
        help="Text input for the chatbot.",
    )

    parser.add_argument(
        "--voice",
        action="store_true",
        help="Enable voice mode for the chatbot.",
    )

    args = parser.parse_args()

    if args.voice:
        chatbot.converse_vocally()
    elif args.text:
        chatbot.respond_with_context(args.text)
    else:
        chatbot.converse() # full text
