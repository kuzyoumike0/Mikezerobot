import discord
from discord.ext import commands
import asyncio
import datetime
import os

class VoiceRecorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vc = None
        self.recording = False
        self.ffmpeg_process = None
        self.audio_filename = None

    @commands.command()
    async def joinrec(self, ctx):
        """ボイスチャンネルに参加して録音開始"""
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send("❌ 先にボイスチャンネルに参加してください。")
            return

        if self.vc and self.vc.is_connected():
            await ctx.send("⚠️ すでに録音中です。")
            return

        channel = ctx.author.voice.channel
        self.vc = await channel.connect()
        await ctx.send(f"🔴 録音を開始しました: `{channel.name}`")

        # 録音ファイルの準備
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.audio_filename = f"recording_{timestamp}.wav"
        os.makedirs("recordings", exist_ok=True)
        filepath = os.path.join("recordings", self.audio_filename)

        # ffmpeg録音プロセス
        self.ffmpeg_process = await asyncio.create_subprocess_exec(
            'ffmpeg',
            '-f', 's16le',
            '-ar', '48000',
            '-ac', '2',
            '-i', 'pipe:0',
            filepath,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        # 音声受信を開始
        self.recording = True
        self.bot.loop.create_task(self.record_audio_loop())

    async def record_audio_loop(self):
        """VCから音声データを取得してffmpegに渡す"""
        while self.recording and self.vc and self.vc.is_connected():
            await asyncio.sleep(1)  # ※詳細な録音処理は外部音声ライブラリに依存
            # Discord.py では直接録音できない。実際は voice-receive 拡張が必要。
            pass  # 本格的な録音には別ライブラリが必要（下記補足参照）

    @commands.command()
    async def stoprec(self, ctx):
        """録音を停止してファイルを送信"""
        if not self.vc or not self.vc.is_connected():
            await ctx.send("⚠️ 録音中ではありません。")
            return

        self.recording = False
        await self.vc.disconnect()
        self.vc = None

        if self.ffmpeg_process:
            self.ffmpeg_process.stdin.close()
            await self.ffmpeg_process.wait()
            self.ffmpeg_process = None

        filepath = os.path.join("recordings", self.audio_filename)
        if os.path.exists(filepath):
            await ctx.send("✅ 録音完了。ファイルを送信します。")
            await ctx.send(file=discord.File(filepath))
        else:
            await ctx.send("❌ 録音ファイルが見つかりませんでした。")

    @commands.command()
    async def vcstatus(self, ctx):
        """録音状態を確認"""
        if self.recording and self.vc:
            await ctx.send("🔴 録音中です。")
        else:
            await ctx.send("⏹️ 録音していません。")

async def setup(bot):
    await bot.add_cog(VoiceRecorder(bot))
