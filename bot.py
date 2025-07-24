import discord
from discord.ext import commands
import asyncio
import os
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

TOKEN = os.getenv("TOKEN")  # .env や環境変数から取得済みと仮定

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

async def load_all_extensions():
    logger.info("拡張機能のロードを開始します。")
    cogs_dir = "./cogs"
    if not os.path.exists(cogs_dir):
        logger.warning(f"{cogs_dir} フォルダが存在しません。")
        return

    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            extension = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(extension)
                logger.info(f"✅ Loaded: {extension}")
            except Exception as e:
                logger.error(f"❌ Failed to load {extension}: {e}")

@bot.event
async def on_ready():
    logger.info(f"Bot is ready: {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_command_error(ctx, error):
    logger.error(f"コマンドエラー: {ctx.command} で例外発生: {error}")

async def main():
    logger.info("Bot起動処理を開始します。")
    await load_all_extensions()
    logger.info("全拡張機能のロード完了。Botを起動します。")
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
