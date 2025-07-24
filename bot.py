import discord
from discord.ext import commands
import asyncio
import os
import traceback

# トークンの読み込み（.env や環境変数から）
TOKEN = os.getenv("TOKEN")  # Railwayでは .env に設定する

# コマンドプレフィックスとインテント（message_contentを明示的に有効化）
intents = discord.Intents.all()
intents.message_content = True  # ← 重要！

bot = commands.Bot(command_prefix="!", intents=intents)

# 起動メッセージ
@bot.event
async def on_ready():
    print(f"✅ Botとしてログインしました: {bot.user}（ID: {bot.user.id}）")

# エラー表示（デバッグ用）
@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"⚠️ コマンドエラー: {error}")
    traceback.print_exception(type(error), error, error.__traceback__)

# 起動処理
async def main():
    async with bot:
        # 読み込みたいCog（複数あるならリストで追加）
        cogs = [
            "cogs.server_pet_cog_buttons"
        ]
        for cog in cogs:
            try:
                await bot.load_extension(cog)
                print(f"✅ 歯車 '{cog}' を読み込みました")
            except Exception as e:
                traceback.print_exc()  # 詳細なエラー表示
                print(f"❌ 歯車 '{cog}' の読み込みに失敗しました: {e}")
        await bot.start(TOKEN)

# Flask（Railway対策・KeepAlive）
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running."

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 起動
if __name__ == "__main__":
    keep_alive()  # Flaskサーバー起動
    asyncio.run(main())  # Bot起動
