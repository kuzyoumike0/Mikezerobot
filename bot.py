import os
import discord
from discord.ext import commands
from config import TOKEN
import asyncio
from keep_alive import keep_alive
from bump_task import BumpNotifier  # bumpタスククラスを読み込む

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return  # Botの入退室は無視

    print(f"[VC変化] {member.name}: {before.channel} → {after.channel}")

async def load_cogs():
    cogs = [
        "helpme",
        "setupvc",
        "vote",
        "creategroup",
        "vctimer",
        "join_sound",
    ]
    for cog in cogs:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"✅ Loaded cog: {cog}")
        except Exception as e:
            print(f"❌ Failed to load cog {cog}: {e}")

@bot.event
async def on_ready():
    print(f"[BOT] Logged in as {bot.user.name}")

async def main():
    keep_alive()              # Webサーバー起動（Replit/Railway対策）
    bump = BumpNotifier(bot)  # bumpタスクのインスタンス化と起動（__init__で.start()される想定）
    # bump.start()  # 必要ならここで起動

    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
