import discord
from discord.ext import commands
import asyncio
import os
import sys
import datetime
import platform

class Recorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}

    @commands.command()
    async def joinrec(self, ctx):
        """ボイスチャンネルに参加"""
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            vc = await channel.connect()
            self.voice_clients[ctx.guild.id] = vc
            await ctx.send("✅ ボイスチャンネルに参加しました")
        else:
            await ctx.send("⚠️ ボイスチャンネルに参加していません")

    @commands.command()
    async def recstop(self, ctx):
        """ボイスチャンネルから退出"""
        vc = self.voice_clients.get(ctx.guild.id)
        if vc:
            await vc.disconnect()
            del self.voice_clients[ctx.guild.id]
            await ctx.send("👋 ボイスチャンネルから切断しました")
        else:
            await ctx.send("⚠️ まだ接続されていません")

    @commands.command()
    async def record(self, ctx, duration: int = 10):
        """
        音声を録音（例: !record 10）
        duration秒後に自動停止
        """
        vc = self.voice_clients.get(ctx.guild.id)
        if not vc:
            await ctx.send("⚠️ ボイスチャンネルに接続していません")
            return

        os.makedirs("recordings", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"recordings/recording_{ctx.guild.id}_{timestamp}.wav"

        system = platform.system()
        if system == "Windows":
            # Windowsは dshow を使う（録音デバイス名は環境により異なる）
            input_device = "audio=マイク"  # 必要に応じて変更してください
            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "dshow",
                "-i", input_device,
                "-t", str(duration),
                filename
            ]
        elif system == "Darwin":
            # macOSは avfoundation を使う
            input_device = ":0"  # 0はデフォルトデバイス
            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "avfoundation",
                "-i", input_device,
                "-t", str(duration),
                filename
            ]
        else:
            # Linuxは PulseAudio (pipewireも同様) を使う
            # 'default' ではなく、利用可能なソース名を pactl list sources short で確認し指定してください
            input_device = "default"  # ここを実際のPulseAudioソース名に書き換えが必要
            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "pulse",
                "-i", input_device,
                "-t", str(duration),
                filename
            ]

        await ctx.send(f"🎙️ 録音開始（{duration}秒）...")

        try:
            process = await asyncio.create_subprocess_exec(*ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                await ctx.send(f"✅ 録音終了: {filename}")
            else:
                await ctx.send(f"❌ 録音失敗。FFmpegエラー:\n```{stderr.decode()}```")
        except Exception as e:
            await ctx.send(f"❌ 録音に失敗しました: {e}")

async def setup(bot):
    await bot.add_cog(Recorder(bot))
