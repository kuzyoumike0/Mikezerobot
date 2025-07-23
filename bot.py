import discord
from discord.ext import commands
import asyncio

from config import TOKEN  # .envから読み込んだTOKEN（config.pyでload_dotenv済みとする）
from keep_alive import keep_alive  # Railway対策の簡易Webサーバー
from bump_task import BumpNotifier  # BUMP通知用のタスククラス

# Botの設定
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# VCの入退室ログ（任意の機能）
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    print(f"[VC変化] {member.name}: {before.channel} → {after.channel}")

# Cogの読み込み
async def load_cogs():
    cogs = [
        "helpme",
        "setupvc",
        "vote",
        "creategroup",
        "vctimer",
    ]
    for cog in cogs:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"✅ Loaded cog: {cog}")
        except Exception as e:
            print(f"❌ Failed to load cog {cog}: {e}")

# 起動時イベント
@bot.event
async def on_ready():
    print(f"[BOT] Logged in as {bot.user.name}")

# メイン関数
async def main():
    keep_alive()  # Railwayでの永続稼働対策（Webサーバー起動）
    bump = BumpNotifier(bot)  # bump通知タスクの起動（コンストラクタで.start()想定）

    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

# エントリーポイント
if __name__ == "__main__":
    asyncio.run(main())
