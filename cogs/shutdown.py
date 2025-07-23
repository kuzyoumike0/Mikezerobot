from discord.ext import commands

class ControlCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, ctx):
        await ctx.send("Botをシャットダウンします。")
        await self.bot.close()

async def setup(bot):
    await bot.add_cog(ControlCog(bot))
