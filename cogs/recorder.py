import discord
from discord.ext import commands
from discord.ext import audiorec  # 外部録音ライブラリ
import os

class Recorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rec = audiorec.Recorder()

    @commands.command()
    async def join(self, ctx):
        """ボイスチャットに参加"""
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await self.rec.join(channel)
            await ctx.send("ボイスチャンネルに参加しました。")
        else:
            await ctx.send("ボイスチャンネルに参加していません。")

    @commands.command()
    async def startrec(self, ctx):
        """録音開始"""
        await self.rec.start_recording(ctx.guild)
        await ctx.send("録音を開始しました。")

    @commands.command()
    async def stoprec(self, ctx):
        """録音停止 & ファイル保存"""
        audio = await self.rec.stop_recording(ctx.guild)
        file_path = f"recording_{ctx.guild.id}.wav"
        with open(file_path, "wb") as f:
            f.write(audio.file.read())
        await ctx.send("録音を停止しました。", file=discord.File(file_path))

    @commands.command()
    async def leave(self, ctx):
        """ボイスチャットから退出"""
        await self.rec.disconnect(ctx.guild)
        await ctx.send("ボイスチャンネルから退出しました。")

async def setup(bot):
    await bot.add_cog(Recorder(bot))
