# bot.py
import discord
from discord.ext import commands
import asyncio
import os

TOKEN = os.getenv("TOKEN")  # .env や Railway に設定済みと仮定
intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

async def load_all_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            extension = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(extension)
                print(f"✅ Loaded: {extension}")
            except Exception as e:
                print(f"❌ Failed to load {extension}: {e}")

@bot.event
async def on_ready():
    print(f"Bot is ready: {bot.user.name}")

async def main():
    await load_all_extensions()
    await bot.start(TOKEN)

asyncio.run(main())
