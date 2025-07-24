import os
import sys
from discord.ext import commands

class RestartCog(commands.Cog):  # Cog名を変更
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="restart")
    @commands.is_owner()
    async def restart_bot(self, ctx):
        await ctx.send("Botを再起動します...")
        await self.bot.close()
        # プロセスを自身の実行ファイルで再起動
        os.execv(sys.executable, [sys.executable] + sys.argv)

async def setup(bot):
    await bot.add_cog(RestartCog(bot))
