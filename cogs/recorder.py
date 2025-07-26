import discord
from discord.ext import commands
from discord.ext import audiorec  # 録音用ライブラリ

class Recorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rec = audiorec.Recorder()

    @commands.command(name="joinrec")
    async def joinrec(self, ctx):
        """ボイスチャットに参加"""
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await self.rec.join(channel)
            await ctx.send("🎧 ボイスチャンネルに参加しました。")
        else:
            await ctx.send("❌ あなたはボイスチャンネルに参加していません。")

    @commands.command(name="rec")
    async def start_recording(self, ctx):
        """録音を開始"""
        await self.rec.start_recording(ctx.guild)
        await ctx.send("🔴 録音を開始しました。通話が録音されています。")

    @commands.command(name="recstop")
    async def stop_recording(self, ctx):
        """録音を停止しファイルを送信"""
        audio = await self.rec.stop_recording(ctx.guild)
        file_path = f"recording_{ctx.guild.id}.wav"
        with open(file_path, "wb") as f:
            f.write(audio.file.read())
        await ctx.send("🛑 録音を停止しました。録音ファイルを送信します。", file=discord.File(file_path))

    @commands.command(name="leave")
    async def leave(self, ctx):
        """ボイスチャットから退出"""
        await self.rec.disconnect(ctx.guild)
        await ctx.send("👋 ボイスチャンネルから退出しました。")

    @commands.command(name="helprec")
    async def helprec(self, ctx):
        """録音Botのコマンド説明を表示"""
        help_text = (
            "**🎙 録音Bot コマンド一覧：**\n"
            "```yaml\n"
            "!joinrec   : ボイスチャンネルに参加\n"
            "!rec       : 録音を開始\n"
            "!recstop   : 録音を停止してファイルを送信\n"
            "!leave     : ボイスチャンネルから退出\n"
            "!helprec   : このコマンド一覧を表示\n"
            ```"
        )
        await ctx.send(help_text)

async def setup(bot):
    await bot.add_cog(Recorder(bot))
