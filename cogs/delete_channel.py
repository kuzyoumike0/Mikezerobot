import discord
from discord.ext import commands
from config import DELETE_ALLOWED_CATEGORY_IDS


class DeleteChannel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="delete")
    async def delete(self, ctx: commands.Context):
        channel = ctx.channel

        if not isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
            await ctx.send("❌ このチャンネルは `!delete` で削除できません。")
            return

        if channel.category_id not in DELETE_ALLOWED_CATEGORY_IDS:
            await ctx.send("❌ このチャンネルは削除対象のカテゴリに含まれていないため、`!delete` で削除できません。")
            return

        await ctx.send(f"🗑️ このチャンネル「{channel.name}」を削除します...")
        await channel.delete(reason=f"{ctx.author} が !delete を実行")


async def setup(bot: commands.Bot):
    await bot.add_cog(DeleteChannel(bot))
