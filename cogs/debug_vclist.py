# cogs/debug_vclist.py
import discord
from discord.ext import commands


class DebugVCList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def vclist(self, ctx):
        lines = []
        for ch in ctx.guild.voice_channels:
            lines.append(f"{ch.name} : {ch.id}")
        if not lines:
            await ctx.send("このサーバーでBotが認識しているVCはありません。")
            return
        text = "\n".join(lines)
        await ctx.send(f"Botが認識しているVC一覧:\n```\n{text}\n```")


async def setup(bot: commands.Bot):
    await bot.add_cog(DebugVCList(bot))
