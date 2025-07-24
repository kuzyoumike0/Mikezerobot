# cogs/daily_quote.py

import discord
from discord.ext import commands, tasks
import datetime
import random

from config import DAILY_POST_CHANNEL_ID

class DailyQuote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.quotes = self.load_quotes()
        self.daily_quote_task.start()

    def cog_unload(self):
        self.daily_quote_task.cancel()

    def load_quotes(self):
        try:
            with open("data/quotes.txt", "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            return ["✨ 今日も一日がんばろう！"]

    @tasks.loop(time=datetime.time(hour=10, tzinfo=datetime.timezone(datetime.timedelta(hours=9))))
    async def daily_quote_task(self):
        channel = self.bot.get_channel(DAILY_POST_CHANNEL_ID)
        if channel:
            quote = random.choice(self.quotes)
            embed = discord.Embed(
                title="🌞 今日のひとこと",
                description=quote,
                color=discord.Color.orange()
            )
            await channel.send(embed=embed)

def setup(bot):
    bot.add_cog(DailyQuote(bot))
