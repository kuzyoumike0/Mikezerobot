import discord
from discord.ext import commands

class CreateGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[CreateGroup] Cog initialized.")

    async def cog_load(self):
        print("[CreateGroup] cog_load started.")
        await self.load_persistent_views()
        print("[CreateGroup] persistent views loaded.")

    # load_persistent_viewsはそのまま残す

