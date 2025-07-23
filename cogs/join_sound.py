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
        self.target_channel_id = None  # !joinvc 実行時にセットされるVCのID

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
        # BotがVCに未接続なら無視
        if not self.voice_client or not self.voice_client.is_connected():
            return

        # 監視対象のVC IDが未設定なら無視
        if not self.target_channel_id:
            return

        # Bot自身の入退室も無視
        if member.bot:
            return

        # 変化が対象VCに関係なければ無視
        if before.channel == after.channel:
            return
        if (before.channel and before.channel.id != self.target_channel_id) and \
           (after.channel and after.channel.id != self.target_channel_id):
            return

        # 入室時の処理
        if after.channel and after.channel.id == self.target_channel_id:
            se_file = self.get_join_sound_by_time()
            await self.play_se(se_file)

        # 退室時の処理
        elif before.channel and before.channel.id == self.target_channel_id:
            await self.play_se("sounds/leave.mp3")

    def get_join_sound_by_time(self):
        """現在のJST時間帯に応じて適切なSEファイルパスを返す"""
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
        """指定SEを再生し、その後に無音を再開"""
        if self.voice_client and self.voice_client.is_connected():
            # 他のSEが再生中なら待つ
            while self.voice_client.is_playing():
                await asyncio.sleep(0.1)

            # SEを再生
            se_source = discord.FFmpegPCMAudio(filepath)
            self.voice_client.play(se_source)

            # SE終了待ち
            while self.voice_client.is_playing():
                await asyncio.sleep(0.1)

            # 無音を再開
            silence_source = discord.FFmpegPCMAudio("sounds/silence.mp3")
            self.voice_client.play(silence_source)

# 非同期Cogセットアップ関数（main側で await bot.load_extension に対応）
async def setup(bot):
    await bot.add_cog(JoinSound(bot))
