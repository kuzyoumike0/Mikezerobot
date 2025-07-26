import discord
from discord.ext import commands
import asyncio
import os
import logging
from dotenv import load_dotenv

# .envファイルから環境変数をロード
load_dotenv()

# ロギング設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("discord_bot")

# TOKENの取得
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    logger.error("❌ TOKENが設定されていません。`.env`ファイルまたは環境変数を確認してください。")
    exit(1)

# Discord Intents 設定（録音Botには voice_states が必要）
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

# Bot本体
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
                logger.error(f"❌ 拡張読み込み失敗: {extension}\n{e}")

# --- Botイベント定義 ---
@bot.event
async def on_ready():
    logger.info(f"✅ Bot起動完了: {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_command_error(ctx, error):
    logger.error(f"⚠️ コマンドエラー: {ctx.command} - {error}")
    await ctx.send(f"❌ コマンド実行中にエラーが発生しました。\n```{error}```")

# --- メイン起動関数 ---
async def main():
    logger.info("🚀 Bot起動処理を開始します。")
    await load_all_extensions()
    logger.info("✅ すべての拡張機能をロードしました。")
    await bot.start(TOKEN)

# --- スクリプト実行 ---
if __name__ == "__main__":
    asyncio.run(main())
