import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    print("[ERROR] TOKEN環境変数が設定されていません。Botは起動しません。")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[INFO] Bot is ready: {bot.user.name} (ID: {bot.user.id})")

@bot.event
async def on_command_error(ctx, error):
    print(f"[ERROR] コマンドエラー: {ctx.command} で例外発生: {error}")

if __name__ == "__main__":
    print("[INFO] Bot起動処理を開始します。")
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"[ERROR] Botが例外で停止しました: {e}")
