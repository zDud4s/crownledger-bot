# bot/main.py
import os
import sys
import logging
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
)

load_dotenv()
# --- garantir que o ROOT do projeto entra no sys.path ---
ROOT = Path(__file__).resolve().parents[1]  # .../crownledger-bot
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN não está definido no ambiente (.env).")

GUILD_ID = int(os.getenv("GUILD_ID", "0"))  # recomendado em dev para sync instantâneo

intents = discord.Intents.default()


class CrownLedgerBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",  # pode ficar, mesmo que só uses /
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self):
        # 1) Carregar cogs/extensions
        extensions = [
            "bot.commands.rank",  # tem de existir app/commands/rank.py
        ]

        for ext in extensions:
            try:
                await self.load_extension(ext)
                logging.info("Loaded extension: %s", ext)
            except Exception as e:
                logging.exception("Failed to load extension %s: %s", ext, e)

        # 2) Sync dos slash commands (depois de carregar cogs)
        try:
            if GUILD_ID:
                guild = discord.Object(id=GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logging.info(
                    "Synced %d command(s) to guild %s: %s",
                    len(synced),
                    GUILD_ID,
                    [c.name for c in synced],
                )
            else:
                synced = await self.tree.sync()
                logging.info(
                    "Synced %d global command(s): %s",
                    len(synced),
                    [c.name for c in synced],
                )
        except Exception as e:
            logging.exception("Slash command sync failed: %s", e)

    async def on_ready(self):
        logging.info("Logged in as %s (id=%s)", self.user, self.user.id)


def main():
    bot = CrownLedgerBot()
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
