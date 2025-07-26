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

    @commands.command()
    async def join(self, ctx):
        """ボイスチャンネルに参加"""
        if ctx.author.voice:
            channel = ctx.author.voice.channel
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

        # 録音ファイル名
        filename = f"recordings/recording_{ctx.guild.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"
        os.makedirs("recordings", exist_ok=True)

        # ffmpeg を使って録音（bot 自身の受信音声のみ）
        ffmpeg_cmd = [
            "ffmpeg",
            "-f", "dshow" if os.name == "nt" else "avfoundation",
            "-i", "audio=",
            "-t", str(duration),
            filename
        ]

        await ctx.send(f"🎙️ 録音開始（{duration}秒）...")

        try:
            process = await asyncio.create_subprocess_exec(*ffmpeg_cmd)
            await process.wait()
            await ctx.send(f"✅ 録音終了: {filename}")
        except Exception as e:
            await ctx.send(f"❌ 録音に失敗しました: {e}")

async def setup(bot):
    await bot.add_cog(Recorder(bot))
