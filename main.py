import os
import discord
from discord.ext import commands
from config import TOKEN
import asyncio
from keep_alive import keep_alive
from bump_task import BumpNotifier
import traceback

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    print(f"[VC変化] {member.name}: {before.channel} → {after.channel}")

async def load_cogs():
    cogs = [
        "helpme",
        "setupvc",
        "vote",
        "creategroup",
        "vctimer",
        "join_sound",
        "setup_secret",
        "server_pet_cog_buttons",
    ]
    for cog in cogs:
        try:
            print(f"📂 Loading cog: {cog} ...")
            await bot.load_extension(f"cogs.{cog}")
            print(f"✅ Loaded cog: {cog}")
        except Exception as e:
            print(f"❌ Failed to load cog {cog}: {e}")
            traceback.print_exc()

@bot.event
async def on_ready():
    print(f"[BOT] Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Guilds: {[guild.name for guild in bot.guilds]}")

async def main():
    print(f"DEBUG: TOKEN is {'set' if TOKEN else 'not set'}")
    if TOKEN is None or TOKEN == "":
        print("⚠️ TOKENが設定されていません。環境変数を確認してください。")
        return

    keep_alive()  # 必要なければコメントアウトしてOK

    bump = BumpNotifier(bot)  # ループは__init__内でstartされる想定

    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
