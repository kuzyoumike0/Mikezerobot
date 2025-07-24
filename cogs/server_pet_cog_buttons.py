import discord
from discord.ext import commands

class ServerPetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pet")
    async def pet(self, ctx):
        await ctx.send("ペットを呼び出しました！")

# これが Cog 読み込みのエントリーポイント
async def setup(bot):
    await bot.add_cog(ServerPetCog(bot))
