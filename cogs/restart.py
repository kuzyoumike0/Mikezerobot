import os
import sys
import discord
from discord.ext import commands
from config import MOD_ROLE_ID


def is_owner_or_mod():
    async def predicate(ctx: commands.Context) -> bool:
        if await ctx.bot.is_owner(ctx.author):
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        if discord.utils.get(ctx.author.roles, id=MOD_ROLE_ID):
            return True
        return False
    return commands.check(predicate)


class RestartCog(commands.Cog):  # Cog名を変更
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="restart")
    @is_owner_or_mod()
    async def restart_bot(self, ctx):
        await ctx.send("Botを再起動します...")
        await self.bot.close()
        # プロセスを自身の実行ファイルで再起動
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @restart_bot.error
    async def restart_bot_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("❌ このコマンドはBot所有者・管理者・管理人ロールのみ使用できます。")
        else:
            print(f"[ERROR] restart: {error}")
            await ctx.send("エラーが発生しました。")

async def setup(bot):
    await bot.add_cog(RestartCog(bot))
