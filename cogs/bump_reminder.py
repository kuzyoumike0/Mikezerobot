from discord.ext import tasks, commands
from datetime import datetime, timedelta
from config import BUMP_CHANNEL_ID


class BumpReminder(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.last_bump_time = None
        self.bump_reminder.start()

    @tasks.loop(minutes=1)
    async def bump_reminder(self):
        now = datetime.utcnow()
        if self.last_bump_time is None or now - self.last_bump_time >= timedelta(hours=2):
            channel = self.bot.get_channel(BUMP_CHANNEL_ID)
            if channel:
                await channel.send("BUMPをお願いします！")
                self.last_bump_time = now

    @bump_reminder.before_loop
    async def before_bump(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(BumpReminder(bot))
