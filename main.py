import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import traceback

load_dotenv()
TOKEN = os.getenv("TOKEN")
print(f"Using token: {'***' if TOKEN else 'No token found!'}")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

async def load_cogs():
    cogs = [
        "helpme",
        "creategroup",
        "setupvc",
        "vctimer",
        "vote",
        "exit_handler",
        "bump_reminder",
        "join_sound",
        "shutdown",       # ここにshutdown Cog
        "restart",         # ここにrestart Cogを追加
        "setup_secret",
    ]
    for cog in cogs:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"✅ Loaded cog: {cog}")
        except Exception:
            print(f"❌ Failed to load cog {cog}:")
            traceback.print_exc()

@bot.event
async def on_ready():
    print(f"🟢 Logged in as {bot.user} (ID: {bot.user.id})")

async def main():
    await load_cogs()
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
