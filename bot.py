import discord
from discord.ext import commands
import asyncio

# config.pyからのインポートは、循環参照防止のため関数内やイベント内で行う場合がありますが、
# ここではTOKENだけはグローバルでインポート。
from config import TOKEN

# keep_aliveはサーバーキープ用（Railway向け）
from keep_alive import keep_alive

# BumpNotifierはBUMP通知のクラス、start()が内部で呼ばれる想定
from bump_task import BumpNotifier


intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user.name} (ID: {bot.user.id})")


@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    # configからVC_CHANNEL_ID, get_join_sound, get_leave_soundはここで遅延インポートして循環回避
    from config import VC_CHANNEL_ID, get_join_sound, get_leave_sound

    # 入室時の処理
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

    # 退室時の処理
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


async def main():
    keep_alive()  # RailwayのWebサーバー起動（なければ削除可）
    BumpNotifier(bot)  # BUMP通知タスク起動（.start()は内部で呼ばれる想定）

    async with bot:
        await load_cogs()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
