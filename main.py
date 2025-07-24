import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

# .env ファイルから TOKEN を読み込む（Railwayやローカル開発用）
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Botのインテントとプレフィックス
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Bot起動時のイベント
@bot.event
async def on_ready():
    print(f"✅ Bot起動完了: {bot.user} (ID: {bot.user.id})")

# cogs フォルダ内のすべての cog を読み込む関数
async def load_all_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            extension = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(extension)
                print(f"✅ Cog 読み込み成功: {extension}")
            except Exception as e:
                print(f"❌ Cog 読み込み失敗: {extension}")
                print(e)

# 非同期の main 実行関数
async def main():
    await load_all_cogs()
    await bot.start(TOKEN)

# 実行
if __name__ == "__main__":
    asyncio.run(main())
