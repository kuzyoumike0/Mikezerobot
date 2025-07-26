import discord
from discord.ext import commands
import asyncio
import os
import subprocess
import datetime

class Recorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}

    @commands.command(name="joinrec")
    async def joinrec(self, ctx):
        """ボイスチャンネルに参加"""
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            if ctx.guild.id in self.voice_clients:
                await ctx.send("⚠️ すでにボイスチャンネルに接続しています。")
                return
            vc = await channel.connect()
            self.voice_clients[ctx.guild.id] = vc
            await ctx.send("✅ ボイスチャンネルに参加しました")
        else:
            await ctx.send("⚠️ ボイスチャンネルに参加していません")

    @commands.command()
    async def leave(self, ctx):
        """ボイスチャンネルから退出"""
        vc = self.voice_clients.get(ctx.guild.id)
        if vc:
            await vc.disconnect()
            del self.voice_clients[ctx.guild.id]
            await ctx.send("👋 切断しました")
        else:
            await ctx.send("⚠️ まだ接続されていません")

    @commands.command()
    async def record(self, ctx, duration: int = 10):
        """
        音声を録音（例: !record 10）
        ※ duration（秒数）後に自動で停止
        """
        vc = self.voice_clients.get(ctx.guild.id)
        if not vc:
            await ctx.send("⚠️ ボイスチャンネルに接続していません")
            return

        # 録音用フォルダ作成
        os.makedirs("recordings", exist_ok=True)

        # 録音ファイル名
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"recordings/recording_{ctx.guild.id}_{timestamp}.mp3"

        await ctx.send(f"🎙️ 録音開始（{duration}秒）...")

        # ffmpeg で録音を開始（Discordの音声受信を直接録音するには複雑なので、下記は録音の枠組み例）
        # 注意: Windows/Linux/Macでの録音入力デバイス名は環境により異なります。適宜調整してください。
        if os.name == "nt":
            input_device = "audio=マイク名など"
            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "dshow",
                "-i", input_device,
                "-t", str(duration),
                filename
            ]
        elif os.name == "posix":
            input_device = ":0"  # macOSの例。LinuxはALSAやPulseAudio設定による
            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "avfoundation",
                "-i", input_device,
                "-t", str(duration),
                filename
            ]
        else:
            await ctx.send("❌ このOSでは録音がサポートされていません。")
            return

        try:
            process = await asyncio.create_subprocess_exec(*ffmpeg_cmd,
                                                           stdout=asyncio.subprocess.PIPE,
                                                           stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                await ctx.send(f"✅ 録音終了: {filename}", file=discord.File(filename))
            else:
                await ctx.send(f"❌ 録音に失敗しました。ffmpegエラー:\n```{stderr.decode()}```")
        except Exception as e:
            await ctx.send(f"❌ 録音中にエラーが発生しました: {e}")

async def setup(bot):
    await bot.add_cog(Recorder(bot))
