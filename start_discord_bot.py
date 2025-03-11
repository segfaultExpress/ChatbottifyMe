import discord
import json
from discord.ext import commands
from chatbot import Chatbot
import logging
import os

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
bot = commands.Bot(command_prefix="!", intents=intents)
discord_chatbot = Chatbot()

@bot.event
async def on_ready():
    """Triggered when the bot starts."""
    print(f'Logged in as {bot.user}')
    for guild in bot.guilds:
        if str(guild.id) not in guild_channel_map:
            await find_default_channel(guild, first_time=True)
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
