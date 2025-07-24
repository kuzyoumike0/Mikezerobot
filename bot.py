import discord
from discord.ext import commands
import os
import logging
import asyncio

# ここでロギング設定をする（ファイル先頭近く）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

TOKEN = os.getenv("TOKEN")
if TOKEN is None:
    logger.error("[ERROR] TOKEN環境変数が設定されていません。Botは起動しません。")
    exit(1)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Bot is ready: {bot.user} (ID: {bot.user.id})")
    print("==== on_ready イベント発生 ====")

async def main():
    logger.info("[INFO] Bot起動処理を開始します。")
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
