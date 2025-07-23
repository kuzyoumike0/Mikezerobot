import discord
from discord.ext import commands
from datetime import datetime
import os


class ExportLog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="exportlog")
    async def export_log(self,
                         ctx,
                         channel: discord.TextChannel,
                         fmt: str = "txt"):
        """指定したチャンネルのログを txt または html で出力"""
        if fmt not in ["txt", "html"]:
            await ctx.send("形式は `txt` または `html` を指定してください。")
            return

        if not channel.permissions_for(ctx.author).read_messages:
            await ctx.send("そのチャンネルを閲覧する権限がありません。")
            return

        messages = []
        async for message in channel.history(limit=1000, oldest_first=True):
            time = message.created_at.strftime('%Y-%m-%d %H:%M')
            name = message.author.display_name
            content = message.clean_content
            messages.append((time, name, content))

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"log_{channel.name}_{timestamp}.{fmt}"
        filepath = f"/tmp/{filename}"

        if fmt == "txt":
            with open(filepath, "w", encoding="utf-8") as f:
                for time, name, content in messages:
                    f.write(f"[{time}] {name}: {content}\n")
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("<html><body><pre style='font-family:monospace;'>\n")
                for time, name, content in messages:
                    f.write(f"[{time}] <b>{name}</b>: {content}<br>\n")
                f.write("</pre></body></html>")

        try:
            await ctx.author.send(file=discord.File(filepath))
            await ctx.send("ログをDMで送信しました。")
        except discord.Forbidden:
            await ctx.send("DMを送信できませんでした。DMを開放してください。")

        os.remove(filepath)


async def setup(bot):
    await bot.add_cog(ExportLog(bot))
