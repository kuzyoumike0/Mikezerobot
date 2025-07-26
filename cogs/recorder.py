import discord
from discord.ext import commands
import asyncio
import subprocess
import sys
import os
import datetime
import re

class Recorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}
        self.record_process = None

    def detect_windows_audio_device(self):
        """Windows用：利用可能な録音デバイス一覧を取得し、AG03優先で返す"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                capture_output=True,
                text=True,
                check=False,
            )
            output = result.stderr  # デバイスリストはstderrに出る
            devices = []
            audio_device_pattern = re.compile(r'\[dshow @ .*\] *"([^"]+)" *\(audio\)')
            for line in output.splitlines():
                match = audio_device_pattern.search(line)
                if match:
                    devices.append(match.group(1))
            devices_lower = [d.lower() for d in devices]

            for dev in devices:
                if "ag03" in dev.lower():
                    return f'audio={dev}'

            for dev in devices:
                if "virtual-audio-capturer" in dev.lower():
                    return f'audio={dev}'

            for dev in devices:
                if "ステレオミキサー" in dev or "stereo mix" in dev.lower():
                    return f'audio={dev}'

            if devices:
                return f'audio={devices[0]}'

            return None
        except Exception as e:
            print(f"[ERROR] Windows audio device detection failed: {e}")
            return None

    @commands.command()
    async def joinrec(self, ctx):
        """ボイスチャンネルに参加して録音準備"""
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            if ctx.voice_client is not None:
                await ctx.send("⚠️ すでにボイスチャンネルに接続しています。")
                return
            vc = await channel.connect()
            self.voice_clients[ctx.guild.id] = vc
            await ctx.send("✅ ボイスチャンネルに参加しました。録音準備完了。")
        else:
            await ctx.send("⚠️ あなたはボイスチャンネルに参加していません。")

    @commands.command()
    async def stoprec(self, ctx):
        """録音停止しファイルを保存して送信"""
        if ctx.guild.id not in self.voice_clients:
            await ctx.send("⚠️ ボイスチャンネルに接続していません。")
            return

        if self.record_process is None:
            await ctx.send("⚠️ 録音は開始されていません。")
            return

        self.record_process.terminate()
        await asyncio.sleep(1)
        self.record_process = None

        filename = self.current_recording_file
        if os.path.exists(filename):
            await ctx.send(f"🛑 録音を停止しました。録音ファイルを送信します。", file=discord.File(filename))
        else:
            await ctx.send("❌ 録音ファイルが見つかりません。")

    @commands.command()
    async def record(self, ctx, duration: int = 60):
        """録音開始（!record [秒数]）"""
        if ctx.guild.id not in self.voice_clients:
            await ctx.send("⚠️ ボイスチャンネルに接続していません。")
            return

        if self.record_process:
            await ctx.send("⚠️ 録音はすでに開始されています。")
            return

        audio_device = None
        if sys.platform == "win32":
            audio_device = self.detect_windows_audio_device()
            if audio_device is None:
                await ctx.send("❌ Windowsの録音デバイスが見つかりませんでした。")
                return
        else:
            await ctx.send("❌ 現状このBotはWindowsのみ対応です。")
            return

        filename = f"recordings/recording_{ctx.guild.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
        os.makedirs("recordings", exist_ok=True)

        ffmpeg_cmd = [
            "ffmpeg",
            "-f", "dshow",
            "-i", audio_device,
            "-t", str(duration),
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            filename,
        ]

        await ctx.send(f"🎙️ 録音開始（{duration}秒）... デバイス: {audio_device}")

        self.record_process = await asyncio.create_subprocess_exec(*ffmpeg_cmd)
        self.current_recording_file = filename

    @commands.command()
    async def leaverec(self, ctx):
        """ボイスチャンネルから退出"""
        vc = self.voice_clients.get(ctx.guild.id)
        if vc:
            if self.record_process:
                self.record_process.terminate()
                self.record_process = None
            await vc.disconnect()
            del self.voice_clients[ctx.guild.id]
            await ctx.send("👋 ボイスチャンネルから退出しました。")
        else:
            await ctx.send("⚠️ ボイスチャンネルに接続していません。")

    @commands.command(name="helprec")
    async def helprec(self, ctx):
        """録音関連コマンドの使い方を表示"""
        embed = discord.Embed(title="🎙️ 録音Bot コマンド一覧", color=discord.Color.blue())
        embed.add_field(name="!joinrec", value="ボイスチャンネルに参加して録音準備をします。", inline=False)
        embed.add_field(name="!record [秒数]", value="録音を開始します。秒数は任意で指定（デフォルト60秒）。", inline=False)
        embed.add_field(name="!stoprec", value="録音を停止し、録音ファイルを送信します。", inline=False)
        embed.add_field(name="!leaverec", value="ボイスチャンネルから退出します。", inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Recorder(bot))
