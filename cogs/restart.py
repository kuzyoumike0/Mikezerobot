import os
import sys
from discord.ext import commands

class ControlCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def restart(self, ctx):
        await ctx.send("Botを再起動します...")
        await self.bot.close()
        # プロセスを自身の実行ファイルで再起動
        os.execv(sys.executable, [sys.executable] + sys.argv)

async def setup(bot):
    await bot.add_cog(ControlCog(bot))
