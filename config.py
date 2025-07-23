import discord
from discord.ext import commands
import asyncio

from config import TOKEN, get_join_sound, get_leave_sound
from keep_alive import keep_alive  # Railway対策（なければ削除可）
from bump_task import BumpNotifier  # BUMP通知クラス（定義済み想定）

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ====================
# 起動完了イベント
# ====================
@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user.name} (ID: {bot.user.id})")

# ====================
# VC入退室時に音声再生（VC_IDに常駐させておく場合）
# ====================
@bot.event
async def on_voice_state_update(member, before, after):
    from config import VC_CHANNEL_ID
    if member.bot:
        return

    # 入室時
    if after.channel and after.channel.id == VC_CHANNEL_ID and (not before.channel or before.channel.id != VC_CHANNEL_ID):
        sound = get_join_sound()
        if sound:
            try:
                vc = await after.channel.connect()
                vc.play(discord.FFmpegPCMAudio(sound))
                while vc.is_playing():
                    await asyncio.sleep(1)
                await vc.disconnect()
            except Exception as e:
                print(f"[入室音] 再生失敗: {e}")

    # 退室時
    elif before.channel and before.channel.id == VC_CHANNEL_ID and (not after.channel or after.channel.id != VC_CHANNEL_ID):
        sound = get_leave_sound()
        if sound:
            try:
                vc = await before.channel.connect()
                vc.play(discord.FFmpegPCMAudio(sound))
                while vc.is_playing():
                    await asyncio.sleep(1)
                await vc.disconnect()
            except Exception as e:
                print(f"[退室音] 再生失敗: {e}")

# ====================
# Cog 読み込み
# ====================
async def load_cogs():
    cogs = [
        "helpme",
        "setupvc",
        "vote",
        "creategroup",
        "vctimer",
        "join_sounds",
    ]
    for cog in cogs:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"✅ Loaded cog: {cog}")
        except Exception as e:
            print(f"❌ Failed to load cog {cog}: {e}")

# ====================
# メイン関数
# ====================
async def main():
    keep_alive()  # Railwayでの永続稼働用（なければ削除可）
    BumpNotifier(bot)  # BUMPタスク起動（.start()を内部で呼ぶ前提）

    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

# ====================
# 起動
# ====================
if __name__ == "__main__":
    asyncio.run(main())
