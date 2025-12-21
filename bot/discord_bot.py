import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

from bot.commands import rank

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
rank.setup(bot)


@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")


def run():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set")
    bot.run(TOKEN)
