import discord
from discord.ext import commands
import asyncio
import os
import sys
import datetime

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
            await ctx.send("👋 切断しました")
        else:
            await ctx.send("⚠️ まだ接続されていません")

    @commands.command()
    async def record(self, ctx, duration: int = 10):
        """
        OSの録音デバイスから音声を録音（例: !record 10）
        ※ duration（秒数）後に自動で停止
        """
        vc = self.voice_clients.get(ctx.guild.id)
        if not vc:
            await ctx.send("⚠️ ボイスチャンネルに接続していません")
            return

        # 録音ファイル名作成
        os.makedirs("recordings", exist_ok=True)
        filename = f"recordings/recording_{ctx.guild.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.wav"

        # OS別のffmpegコマンド構築
        if sys.platform == "win32":
            # Windows: dshow デバイス名は適宜確認してください（例: "audio=マイク名"）
            input_device = "audio=マイク (Realtek High Definition Audio)"
            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "dshow",
                "-i", input_device,
                "-t", str(duration),
                filename
            ]
        elif sys.platform == "darwin":
            # macOS: avfoundation のデバイス番号はffmpeg -f avfoundation -list_devices true -i ""で確認可能
            # ここではデフォルトのオーディオ入力(マイク)を使う例
            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "avfoundation",
                "-i", ":0",  # ":0" はマイク入力の例です。環境により変えてください。
                "-t", str(duration),
                filename
            ]
        else:
            # Linux等: PulseAudioやALSAで録音設定を行う必要があります。例としてpulseを利用。
            # 実際には環境に応じてdevice名を変更してください。
            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "pulse",
                "-i", "default",
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
                error_msg = stderr.decode().strip()
                await ctx.send(f"❌ ffmpeg エラー:\n```\n{error_msg}\n```")
        except Exception as e:
            await ctx.send(f"❌ 録音に失敗しました: {e}")

async def setup(bot):
    await bot.add_cog(Recorder(bot))
