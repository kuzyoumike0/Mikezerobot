import discord
from discord.ext import commands
import asyncio
import os
import logging
from dotenv import load_dotenv
import platform
import sys

# .envファイルから環境変数をロード
load_dotenv()

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("discord_bot")

# TOKENの取得
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    logger.error("❌ TOKENが設定されていません。`.env`ファイルまたは環境変数を確認してください。")
    sys.exit(1)

# Discord Intents 設定（録音Botには voice_states が必要）
intents = discord.Intents.all()

# Bot本体の作成
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 拡張機能（Cogs）のロード ---
async def load_all_extensions():
    logger.info("🔄 拡張機能のロードを開始します。")
    cogs_dir = "./cogs"
    if not os.path.exists(cogs_dir):
        logger.warning(f"⚠️ {cogs_dir} フォルダが存在しません。")
        return

    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            extension = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(extension)
                logger.info(f"✅ 拡張読み込み成功: {extension}")
            except Exception as e:
                logger.exception(f"❌ 拡張読み込み失敗: {extension}")

# --- Botイベント定義 ---
@bot.event
async def on_ready():
    logger.info(f"✅ Bot起動完了: {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # 存在しないコマンドは無視
    logger.error(f"⚠️ コマンドエラー: {ctx.command} - {error}")
    try:
        await ctx.send(f"❌ コマンド実行中にエラーが発生しました。\n```{error}```")
    except discord.HTTPException:
        logger.error("⚠️ エラーメッセージの送信に失敗しました。")

# --- メイン起動関数 ---
async def main():
    logger.info(f"🚀 Bot起動処理を開始します。Python: {platform.python_version()}, discord.py: {discord.__version__}")
    await load_all_extensions()
    logger.info("✅ すべての拡張機能をロードしました。")
    await bot.start(TOKEN)

# --- スクリプト実行 ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Botの停止が要求されました。")
    except Exception as e:
        logger.exception(f"💥 致命的なエラーによりBotを停止します: {e}")
