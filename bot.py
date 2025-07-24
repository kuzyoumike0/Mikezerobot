# bot.py
import discord
from discord.ext import commands
import asyncio
import os

TOKEN = os.getenv("TOKEN")  # .env や Railway に設定済みと仮定

if TOKEN is None:
    print("[ERROR] TOKEN環境変数が設定されていません。Botは起動しません。")

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

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

@bot.event
async def on_ready():
    print(f"[INFO] Bot is ready: {bot.user.name} (ID: {bot.user.id})")

@bot.event
async def on_command_error(ctx, error):
    print(f"[ERROR] コマンドエラー: {ctx.command} で例外発生: {error}")

async def main():
    try:
        print("[INFO] Bot起動処理を開始します。")
        await load_all_extensions()
        print("[INFO] 全拡張機能のロード完了。Botを起動します。")
        await bot.start(TOKEN)
    except Exception as e:
        print(f"[ERROR] Botが例外で停止しました: {e}")

asyncio.run(main())
