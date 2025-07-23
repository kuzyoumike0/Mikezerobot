import discord
from discord.ext import commands
from discord.utils import get
import datetime
import pytz
import asyncio
import os

JST = pytz.timezone("Asia/Tokyo")

class JoinSound(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_client = None
        self.target_channel_id = None  # Botが接続するVC ID（初回 !joinvc で決定）

    @commands.command()
    async def joinvc(self, ctx):
        """BotをVCに接続し、無音再生を開始"""
        if ctx.author.voice and ctx.author.voice.channel:
            self.target_channel_id = ctx.author.voice.channel.id
            self.voice_client = await ctx.author.voice.channel.connect()

            # 無音ループ再生
            asyncio.create_task(self.play_silence_loop())
            await ctx.send(f"{ctx.author.voice.channel.name} に参加しました。")
        else:
            await ctx.send("VCに接続してからコマンドを使ってください。")

    async def play_silence_loop(self):
        """silence.mp3 を無限ループ再生"""
        while self.voice_client and self.voice_client.is_connected():
            if not self.voice_client.is_playing():
                source = discord.FFmpegPCMAudio("sounds/silence.mp3")
                self.voice_client.play(source)
            await asyncio.sleep(1)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Bot未接続 or 接続VCが指定されていない
        if not self.voice_client or not self.voice_client.is_connected():
            return
        if not self.target_channel_id:
            return

        # 入室 or 退室したVCが対象VCと一致していなければ無視
        if before.channel == after.channel:
            return
        if (before.channel and before.channel.id != self.target_channel_id) and \
           (after.channel and after.channel.id != self.target_channel_id):
            return

        # Bot自身の出入りは無視
        if member.bot:
            return

        # 入室時のSE再生
        if after.channel and after.channel.id == self.target_channel_id:
            se_file = self.get_join_sound_by_time()
            await self.play_se(se_file)

        # 退室時のSE再生
        elif before.channel and before.channel.id == self.target_channel_id:
            await self.play_se("sounds/leave.mp3")

    def get_join_sound_by_time(self):
        """時間帯に応じたSEファイルを返す"""
        now = datetime.datetime.now(JST).time()

        if datetime.time(4, 0) <= now < datetime.time(10, 0):
            return "sounds/early_morning.mp3"
        elif datetime.time(10, 0) <= now < datetime.time(13, 0):
            return "sounds/morning.mp3"
        elif datetime.time(13, 0) <= now < datetime.time(20, 0):
            return "sounds/afternoon.mp3"
        else:
            return "sounds/night.mp3"

    async def play_se(self, filepath):
        """SEを一時停止して再生"""
        if self.voice_client and self.voice_client.is_connected():
            while self.voice_client.is_playing():
                await asyncio.sleep(0.1)

            self.voice_client.stop()
            self.voice_client.play(discord.FFmpegPCMAudio(filepath))

            # SEが終わるまで待つ
            while self.voice_client.is_playing():
                await asyncio.sleep(0.1)

            # 無音再生再開
            if not self.voice_client.is_playing():
                self.voice_client.play(discord.FFmpegPCMAudio("sounds/silence.mp3"))

def setup(bot):
    bot.add_cog(JoinSound(bot))
