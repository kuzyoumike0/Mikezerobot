from discord.ext import tasks
import datetime
import pytz
import config  # config から ID を読み込む

JST = pytz.timezone("Asia/Tokyo")

class BumpNotifier:
    def __init__(self, bot):
        self.bot = bot
        self.bump_channel_id = config.BUMP_CHANNEL_ID
        self.bump_loop.start()

    @tasks.loop(minutes=120)  # 2時間ごとに実行
    async def bump_loop(self):
        # 日本時間で現在時刻を取得
        now = datetime.datetime.now(JST).strftime("%H:%M")
        channel = self.bot.get_channel(self.bump_channel_id)
        if channel:
            await channel.send(f"{now} - bumpの時間です！ `!d bump` を忘れずに！")

    @bump_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
