import discord
import json
from discord.ext import commands
from audio_chatbot import AudioChatbot # Chatbot but more intense
import logging
from config import OPUS_LIB_PATH
import os
import speech_recognition as sr
from transcription_sink import TranscriptionSink
from discord.ext import voice_recv

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing API key! Set the OPENAI_API_KEY environment variable.")

DISC_BOT_TOKEN = os.getenv("DISC_BOT_TOKEN")
if not DISC_BOT_TOKEN:
    raise ValueError("Missing Discord bot token! Set the DISC_BOT_TOKEN environment variable.")

# File for storing channel configurations
CONFIG_FILE = "discord_channel_config.json"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Keep track of voice clients
voice_clients = {}

# Load channel data
def load_data():
    try:
        with open(CONFIG_FILE, "r") as file:
            data = json.load(file)
            # Ensure each entry is a dictionary and not just an integer
            fixed_data = {}
            for guild_id, value in data.items():
                if isinstance(value, int):  # If old format with only channel_id as an int
                    fixed_data[guild_id] = {"channel_id": value, "welcomed": False}
                else:
                    fixed_data[guild_id] = value  # Keep existing valid data
            return fixed_data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save channel data
def save_data():
    with open(CONFIG_FILE, "w") as file:
        json.dump(guild_channel_map, file, indent=4)

# Load existing channel mappings
guild_channel_map = load_data()

# Create bot with command prefix and required intents
intents = discord.Intents.default()
intents.message_content = True  # REQUIRED to read user messages
intents.voice_states = True  # REQUIRED to join voice channels

bot = commands.Bot(command_prefix="!", intents=intents)
discord_chatbot = AudioChatbot()

@bot.event
async def on_ready():
    """Triggered when the bot starts."""
    print(f'Logged in as {bot.user}')
    for guild in bot.guilds:
        if str(guild.id) not in guild_channel_map:
            await find_default_channel(guild, first_time=True)

    discord.opus.load_opus(OPUS_LIB_PATH)

    if discord.opus.is_loaded():
        print("Opus is successfully loaded!")
    else:
        print("Opus is NOT loaded! Check installation.")

    print("Bot is ready!")

@bot.event
async def on_guild_join(guild):
    """Automatically selects a default channel when added to a new server."""
    await find_default_channel(guild, first_time=True)

async def find_default_channel(guild, first_time=False):
    """Finds the first writable text channel and saves it as default."""
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            guild_id_str = str(guild.id)
            
            # Store the default channel ID
            if guild_id_str not in guild_channel_map:
                guild_channel_map[guild_id_str] = {"channel_id": channel.id, "welcomed": False}

            # Only send welcome message the first time
            if first_time and not guild_channel_map[guild_id_str]["welcomed"]:
                await channel.send("Hello! I'm a bot that Matthew created with 15 years of Messenger data. Use `!set_channel` to choose a different channel.")
                guild_channel_map[guild_id_str]["welcomed"] = True
            
            save_data()
            break

@bot.command()
async def join(ctx):
    """Command to join the user's voice channel."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        vc = await channel.connect(cls=voice_recv.VoiceRecvClient)

        discord_chatbot.set_vc(vc)

        sink = TranscriptionSink(bot, on_silent_callback=on_voice_silence)
        vc.listen(sink)
        await ctx.send("Joined and Listening...")
    else:
        await ctx.send("You must be in a voice channel for me to join.")

async def on_voice_silence(text):
    discord_chatbot.respond_with_context(text)

@bot.command()
async def leave(ctx):
    """Command to leave the voice channel."""
    if ctx.guild.id in voice_clients:
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected.")
        # Stop listening for audio
        # discord_chatbot.stop_listening()

        await ctx.send("Disconnected from the voice channel.")
    else:
        await ctx.send("I'm not in a voice channel.")



@bot.command()
async def set_channel(ctx):
    """Allows users to set the bot's default channel for messages."""
    guild_id_str = str(ctx.guild.id)
    guild_channel_map[guild_id_str] = {"channel_id": ctx.channel.id, "welcomed": True}
    save_data()

    logging.info(f"Set channel for guild {guild_id_str} to {ctx.channel.id}")  # Debugging
    await ctx.send(f"This channel ({ctx.channel.mention}) is now set for bot messages.")

@bot.command()
async def send_message(ctx, *, message: str = "Hello, Discord!"):
    """Sends a message to the configured channel."""
    guild_id_str = str(ctx.guild.id)
    channel_id = guild_channel_map.get(guild_id_str, {}).get("channel_id", ctx.channel.id)
    channel = bot.get_channel(channel_id)

    if channel:
        await channel.send(message)
    else:
        await ctx.send("Error: Channel not found.")

@bot.event
async def on_message(message):
    """Listens to messages in the assigned channel and responds only in the set channel."""
    if message.author == bot.user:
        return  # Prevents bot from responding to itself

    guild_id_str = str(message.guild.id)

    # Get the saved channel ID for this guild
    channel_id = guild_channel_map.get(guild_id_str, {}).get("channel_id")

    # Ensure bot commands are still processed
    if message.content.startswith("!"):
        await bot.process_commands(message)

    if channel_id and message.channel.id != channel_id:
        return  # Ignore messages outside the designated channel

    # Send typing indicator
    async with message.channel.typing():
        # Generate and send the response
        try:
            response = discord_chatbot.respond_with_context(message.content)
        
            await message.channel.send(response)
        except Exception as e:
            await message.channel.send(f"Error generating response: {e}")


# Run the bot
bot.run(DISC_BOT_TOKEN)
