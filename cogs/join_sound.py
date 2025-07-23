import discord
from discord.ext import commands
import datetime
import pytz
import asyncio

JST = pytz.timezone("Asia/Tokyo")

SOUNDS = {
    "silence": "sounds/silence.mp3",
    "early_morning": "sounds/early_morning.mp3",
    "morning": "sounds/morning.mp3",
    "afternoon": "sounds/afternoon.mp3",
    "night": "sounds/night.mp3"
}

class JoinSound(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_client = None
        self.silence_task = None  # ループ管理用タスク

    @commands.command()
    async def joinvc(self, ctx):
        """ボイスチャンネルに接続し、無音ループを再生開始"""
        if ctx.author.voice is None:
            await ctx.send("VCに入ってからコマンドを使ってください。")
            return
        
        channel = ctx.author.voice.channel
        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.move_to(channel)
        else:
            self.voice_client = await channel.connect()
        
        await ctx.send(f"{channel.name} に接続しました。")

        # 無音ループ再生をタスクで開始（既にあればキャンセルして再起動）
        if self.silence_task and not self.silence_task.done():
            self.silence_task.cancel()
            try:
                await self.silence_task
            except asyncio.CancelledError:
                pass
        self.silence_task = asyncio.create_task(self.play_silence_loop())

    @commands.command()
    async def leavevc(self, ctx):
        """ボイスチャンネルから切断する"""
        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect()
            self.voice_client = None
            if self.silence_task and not self.silence_task.done():
                self.silence_task.cancel()
                try:
                    await self.silence_task
                except asyncio.CancelledError:
                    pass
            await ctx.send("VCから切断しました。")
        else:
            await ctx.send("現在接続されていません。")

    async def play_silence_loop(self):
        """無音音声を連続再生するループタスク"""
        try:
            while self.voice_client and self.voice_client.is_connected():
                if self.voice_client.is_playing():
                    self.voice_client.stop()
                source = discord.FFmpegPCMAudio(SOUNDS["silence"])
                self.voice_client.play(source)
                # 無音音源の長さを把握している場合は正確に待つ（例: 5秒）
                # ここは適宜調整してください（とりあえず5秒仮定）
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            # タスクキャンセル時は何もしないで終了
            pass
        except Exception as e:
            print(f"play_silence_loop error: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # ボイスクライアントが無効なら無視
        if not self.voice_client or not self.voice_client.is_connected():
            return

        target_channel = self.voice_client.channel

        # VC入退室が対象VCであればSE再生
        if before.channel != target_channel and after.channel == target_channel:
            await self.play_se_for_time()
        elif before.channel == target_channel and after.channel != target_channel:
            await self.play_se_for_time()

    async def play_se_for_time(self):
        """時間帯に応じたSEを再生し、その後無音ループ再開"""
        if not self.voice_client or not self.voice_client.is_connected():
            return
        
        now = datetime.datetime.now(JST)
        hour = now.hour

        if 4 <= hour <= 9:
            se = SOUNDS["early_morning"]
        elif 10 <= hour <= 12:
            se = SOUNDS["morning"]
        elif 13 <= hour <= 19:
            se = SOUNDS["afternoon"]
        else:
            se = SOUNDS["night"]

        try:
            if self.voice_client.is_playing():
                self.voice_client.stop()
            
            source = discord.FFmpegPCMAudio(se)
            # 再生終了時に無音ループを再開するコールバック登録
            def after_play(error):
                if error:
                    print(f"SE play error: {error}")
                # 非同期関数を同期コールバックから呼ぶにはcreate_taskで起動
                if self.voice_client and self.voice_client.is_connected():
                    asyncio.create_task(self.play_silence_loop())

            self.voice_client.play(source, after=after_play)
        except Exception as e:
            print(f"play_se_for_time error: {e}")

async def setup(bot):
    await bot.add_cog(JoinSound(bot))
