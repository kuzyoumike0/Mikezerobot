import discord
from discord.ext import commands
from discord.ext import audiorec
import os
from datetime import datetime

class Recorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rec = audiorec.Recorder()

    @commands.command(name="joinrec")
    async def joinrec(self, ctx):
        """ボイスチャットに参加"""
        try:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
                await self.rec.join(channel)
                await ctx.send("🎧 ボイスチャンネルに参加しました。")
            else:
                await ctx.send("❌ あなたはボイスチャンネルに参加していません。")
        except Exception as e:
            await ctx.send(f"⚠ エラーが発生しました: ```\n{e}\n```")

    @commands.command(name="rec")
    async def start_recording(self, ctx):
        """録音を開始"""
        try:
            await self.rec.start_recording(ctx.guild)
            await ctx.send("🔴 録音を開始しました。通話が録音されています。")
        except Exception as e:
            await ctx.send(f"⚠ 録音開始時にエラーが発生しました: ```\n{e}\n```")

    @commands.command(name="recstop")
    async def stop_recording(self, ctx):
        """録音を停止しファイルを保存＆送信"""
        try:
            audio = await self.rec.stop_recording(ctx.guild)

            # recordings フォルダがなければ作成
            os.makedirs("recordings", exist_ok=True)

            # 現在の日付を取得（例：2025-07-26）
            date_str = datetime.now().strftime("%Y-%m-%d")
            file_path = f"recordings/recording_{date_str}.wav"

            # バッファを先頭に戻してから保存
            audio.file.seek(0)
            with open(file_path, "wb") as f:
                f.write(audio.file.read())

            await ctx.send(
                f"🛑 録音を停止しました。録音ファイル（{date_str}）を送信します。",
                file=discord.File(file_path)
            )
        except Exception as e:
            await ctx.send(f"⚠ 録音停止時にエラーが発生しました: ```\n{e}\n```")

    @commands.command(name="leave")
    async def leave(self, ctx):
        """ボイスチャットから退出"""
        try:
            await self.rec.disconnect(ctx.guild)
            await ctx.send("👋 ボイスチャンネルから退出しました。")
        except Exception as e:
            await ctx.send(f"⚠ 切断時にエラーが発生しました: ```\n{e}\n```")

    @commands.command(name="helprec")
    async def helprec(self, ctx):
        """録音Botのコマンド説明を表示"""
        help_text = (
            "**🎙 録音Bot コマンド一覧：**\n"
            "```yaml\n"
            !joinrec   : ボイスチャンネルに参加\n"
            !rec       : 録音を開始\n"
            !recstop   : 録音を停止してファイルを送信\n"
            !leave     : ボイスチャンネルから退出\n"
            !helprec   : このコマンド一覧を表示\n"
            ```"
        )
        await ctx.send(help_text)

async def setup(bot):
    await bot.add_cog(Recorder(bot))
