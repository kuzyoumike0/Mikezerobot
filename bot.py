# bot.py
import discord
from discord.ext import commands
import asyncio
import os

TOKEN = os.getenv("TOKEN")
if TOKEN is None:
    print("[ERROR] TOKEN環境変数が設定されていません。Botは起動しません。")

intents = discord.Intents.all()
intents.message_content = True  # メッセージ内容取得Intentは必須（特にコマンドに必要）

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[INFO] Bot is ready: {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_command_error(ctx, error):
    print(f"[ERROR] コマンドエラー: {ctx.command} で例外発生: {error}")

async def load_all_extensions():
    print("[INFO] 拡張機能のロードを開始します。")
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            extension = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(extension)
                print(f"✅ Loaded: {extension}")
            except Exception as e:
                print(f"❌ Failed to load {extension}: {e}")

async def main():
    print("[INFO] Bot起動処理を開始します。")
    await load_all_extensions()
    print("[INFO] 全拡張機能のロード完了。Botを起動します。")
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
