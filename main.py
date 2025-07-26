import discord
from discord.ext import commands
import asyncio
import os
import logging
from dotenv import load_dotenv

# --- .envファイルから環境変数をロード ---
load_dotenv()

# --- ロギング設定 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("discord_bot")

# --- トークン取得 ---
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    logger.error("❌ TOKENが設定されていません。.envファイルまたは環境変数を確認してください。")
    exit(1)

# --- Discord Intents 設定 ---
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

# --- Botインスタンス作成 ---
bot = commands.Bot(command_prefix="!", intents=intents)


# --- 拡張機能（Cog）のロード関数 ---
async def load_all_cogs():
    logger.info("🔄 Cogのロードを開始します。")
    cogs_dir = "./cogs"
    if not os.path.exists(cogs_dir):
        logger.warning(f"⚠️ {cogs_dir} フォルダが存在しません。")
        return

    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            extension = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(extension)
                logger.info(f"✅ Cog読み込み成功: {extension}")
            except Exception as e:
                logger.error(f"❌ Cog読み込み失敗: {extension}\n{e}")


# --- Bot起動時イベント ---
@bot.event
async def on_ready():
    logger.info(f"✅ Bot起動完了: {bot.user} (ID: {bot.user.id})")


# --- コマンドエラー処理 ---
@bot.event
async def on_command_error(ctx, error):
    logger.error(f"⚠️ コマンドエラー: {ctx.command} - {error}")
    if ctx.command is None:
        return
    try:
        await ctx.send(f"❌ コマンド実行中にエラーが発生しました。\n```{error}```")
    except discord.HTTPException:
        logger.error("⚠️ エラーメッセージの送信に失敗しました。")


# --- メイン実行関数 ---
async def main():
    logger.info("🚀 Bot起動処理を開始します。")
    await load_all_cogs()
    logger.info("✅ すべてのCogをロードしました。Botを起動します。")
    await bot.start(TOKEN)


# --- スクリプト起動時エントリポイント ---
if __name__ == "__main__":
    asyncio.run(main())
