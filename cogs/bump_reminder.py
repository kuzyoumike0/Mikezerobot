import os
import json
from discord.ext import tasks, commands
from datetime import datetime, timedelta
from config import BUMP_CHANNEL_ID

LAST_BUMP_FILE = "data/last_bump.json"  # 保存ファイルのパス

class BumpReminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_bump_time = self.load_last_bump_time()
        self.bump_reminder.start()

    def load_last_bump_time(self):
        """前回のBUMP時間をファイルから読み込む"""
        if not os.path.exists(LAST_BUMP_FILE):
            # ファイルがない場合、現在時刻から2時間前に設定しておく
            return datetime.utcnow() - timedelta(hours=2)
        try:
            with open(LAST_BUMP_FILE, "r") as f:
                data = json.load(f)
                # ファイルの日時を読み込み
                return datetime.fromisoformat(data["last_bump_time"])
        except Exception as e:
            print(f"[ERROR] BUMP時刻の読み込み失敗: {e}")
            # 読み込み失敗時も2時間前に設定して通知をすぐに飛ばさない
            return datetime.utcnow() - timedelta(hours=2)

    def save_last_bump_time(self):
        """前回のBUMP時間をファイルに保存する"""
        try:
            os.makedirs(os.path.dirname(LAST_BUMP_FILE), exist_ok=True)
            with open(LAST_BUMP_FILE, "w") as f:
                json.dump({"last_bump_time": self.last_bump_time.isoformat()}, f)
        except Exception as e:
            print(f"[ERROR] BUMP時刻の保存失敗: {e}")

    @tasks.loop(minutes=1)
    async def bump_reminder(self):
        now = datetime.utcnow()
        if now - self.last_bump_time >= timedelta(hours=2):
            channel = self.bot.get_channel(BUMP_CHANNEL_ID)
            if channel:
                await channel.send("BUMPをお願いします！")
                self.last_bump_time = now
                self.save_last_bump_time()

    @bump_reminder.before_loop
    async def before_bump(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(BumpReminder(bot))
