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
        self.target_channel_id = None  # Botが接続するVC ID（!joinvc 実行で設定）

    @commands.command()
    async def joinvc(self, ctx):
        """BotをVCに接続し、無音再生を開始"""
        if ctx.author.voice and ctx.author.voice.channel:
            self.target_channel_id = ctx.author.voice.channel.id
            self.voice_client = await ctx.author.voice.channel.connect()

            # 無音ループを非同期で開始
            asyncio.create_task(self.play_silence_loop())
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

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # BotがVCに未接続 or 対象VCが未設定 → 無視
        if not self.voice_client or not self.voice_client.is_connected():
            return
        if not self.target_channel_id:
            return

        # Bot自身の入退室は無視
        if member.bot:
            return

        # 対象VC以外の移動は無視
        if before.channel == after.channel:
            return
        if (before.channel and before.channel.id != self.target_channel_id) and \
           (after.channel and after.channel.id != self.target_channel_id):
            return

        # 入室時
        if after.channel and after.channel.id == self.target_channel_id:
            se_file = self.get_join_sound_by_time()
            await self.play_se(se_file)

        # 退室時
        elif before.channel and before.channel.id == self.target_channel_id:
            await self.play_se("sounds/leave.mp3")

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

    async def play_se(self, filepath):
        """指定SEを再生し、再び無音へ戻す"""
        if self.voice_client and self.voice_client.is_connected():
            while self.voice_client.is_playing():
                await asyncio.sleep(0.1)

            # SE再生
            se_source = discord.FFmpegPCMAudio(filepath)
            self.voice_client.play(se_source)

            while self.voice_client.is_playing():
                await asyncio.sleep(0.1)

            # 無音再生再開
            silence_source = discord.FFmpegPCMAudio("sounds/silence.mp3")
            self.voice_client.play(silence_source)

# 非同期 Cog セットアップ関数（mainで await bot.load_extension に対応）
async def setup(bot):
    await bot.add_cog(JoinSound(bot))
