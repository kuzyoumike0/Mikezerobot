import discord
from discord.ext import commands
import datetime
import pytz
import asyncio

# 日本時間のタイムゾーン設定
JST = pytz.timezone("Asia/Tokyo")

class JoinSound(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_client = None
        self.target_channel_id = None  # Botが接続するVC ID
        self.silence_task = None       # 無音ループタスクを管理

    @commands.command()
    async def joinvc(self, ctx):
        """BotをVCに接続し、無音再生を開始"""
        if ctx.author.voice and ctx.author.voice.channel:
            self.target_channel_id = ctx.author.voice.channel.id
            self.voice_client = await ctx.author.voice.channel.connect()

            # 無音ループを非同期で開始
            self.silence_task = asyncio.create_task(self.play_silence_loop())
            await ctx.send(f"{ctx.author.voice.channel.name} に接続しました。")
        else:
            await ctx.send("先にVCに接続してからこのコマンドを使ってください。")

    async def play_silence_loop(self):
        """無音ファイルを継続的にループ再生する"""
        while self.voice_client and self.voice_client.is_connected():
            if not self.voice_client.is_playing():
                source = discord.FFmpegPCMAudio("sounds/silence.mp3")
                self.voice_client.play(source)
            await asyncio.sleep(1)

    async def interrupt_and_play_se(self, se_file):
        """現在の無音再生を中断してSEを再生し、再度無音へ戻す"""
        if not self.voice_client or not self.voice_client.is_connected():
            return

        # 再生中なら停止
        if self.voice_client.is_playing():
            self.voice_client.stop()

        # SE再生
        se_source = discord.FFmpegPCMAudio(se_file)
        self.voice_client.play(se_source)

        while self.voice_client.is_playing():
            await asyncio.sleep(0.1)

        # 無音再生再開
        silence_source = discord.FFmpegPCMAudio("sounds/silence.mp3")
        self.voice_client.play(silence_source)

    def get_join_sound_by_time(self):
        """JST時間に応じて適切な入室SEファイルパスを返す"""
        now = datetime.datetime.now(JST).time()

        if datetime.time(4, 0) <= now < datetime.time(10, 0):
            return "sounds/early_morning.mp3"
        elif datetime.time(10, 0) <= now < datetime.time(13, 0):
            return "sounds/morning.mp3"
        elif datetime.time(13, 0) <= now < datetime.time(20, 0):
            return "sounds/afternoon.mp3"
        else:  # 20:00 ～ 翌03:59
            return "sounds/night.mp3"

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not self.voice_client or not self.voice_client.is_connected():
            return
        if not self.target_channel_id:
            return
        if member.bot:
            return
        if before.channel == after.channel:
            return
        if (before.channel and before.channel.id != self.target_channel_id) and \
           (after.channel and after.channel.id != self.target_channel_id):
            return

        # 入室
        if after.channel and after.channel.id == self.target_channel_id:
            se_file = self.get_join_sound_by_time()
            await self.interrupt_and_play_se(se_file)

        # 退室
        elif before.channel and before.channel.id == self.target_channel_id:
            await self.interrupt_and_play_se("sounds/leave.mp3")

# 非同期 Cog セットアップ関数
async def setup(bot):
    await bot.add_cog(JoinSound(bot))
