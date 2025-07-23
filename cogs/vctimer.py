import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import asyncio


class VCTimer(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def vctimer(self, ctx, minutes: int):
        if minutes < 6:
            await ctx.send("⏰ タイマーは6分以上で設定してください（5分前通知のため）。")
            return

        now = datetime.now(timezone(timedelta(hours=9)))
        end_time = now + timedelta(minutes=minutes)

        async def notify():
            await asyncio.sleep(
                (end_time - timedelta(minutes=5) - now).total_seconds())
            await ctx.send("⏰ 残り **5分** です！")
            await asyncio.sleep(4 * 60)
            await ctx.send("⏰ 残り **1分** です！")
            await asyncio.sleep(60)
            await ctx.send("⏰ タイマー終了しました！")

        await ctx.send(f"⏳ このチャンネルに {minutes} 分のタイマーを設定しました。")
        asyncio.create_task(notify())


async def setup(bot):
    await bot.add_cog(VCTimer(bot))
