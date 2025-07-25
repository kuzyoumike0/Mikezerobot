import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
import random

from config import DAILY_POST_CHANNEL_ID

# 曜日と外見によるメッセージ辞書
DAILY_MESSAGES = {
    "月": {
        "ふわふわ": ["今週もゆっくり始めようふわ～", "無理せずふんわりいけばいいふわ～"],
        "キラキラ": ["月曜から全開モードキラ！", "輝く一週間のスタートキラ！"],
        "カチカチ": ["さあ任務開始だチ。気を引き締めろッチ！"],
        "もちもち": ["のび〜っとストレッチして、がんばろ！もちもち！"]
    },
    "火": {
        "ふわふわ": ["火曜日ってなんか眠いふわ…", "のんびり火曜日、ちょっと休んでもいいんじゃないかふわ？"],
        "キラキラ": ["今日もチャンスに満ちてるキラ！", "輝きを忘れずに！キラ"],
        "カチカチ": ["計画通りに進めようッチ。", "火は熱いが冷静にッチ。"],
        "もちもち": ["もっちり集中デーだよ！もちもち～！"]
    },
    # 以下略（必要に応じて全曜日追加してください）
}

class DailyQuote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_task.start()

    def cog_unload(self):
        self.daily_task.cancel()

    @tasks.loop(minutes=1)
    async def daily_task(self):
        now = datetime.now(timezone(timedelta(hours=9)))  # 日本時間
        if now.hour == 10 and now.minute == 0:
            channel = self.bot.get_channel(DAILY_POST_CHANNEL_ID)
            if channel is None:
                return

            # ペットの性格取得（固定1匹想定）
            pet = self.load_pet()
            personality = pet.get("personality", "ふわふわ")

            # 曜日を取得
            weekday_jp = ["月", "火", "水", "木", "金", "土", "日"][now.weekday()]

            messages = DAILY_MESSAGES.get(weekday_jp, {}).get(personality, ["今日もがんばろう！"])
            message = random.choice(messages)

            # 既に同日投稿があれば削除（1メッセージに限定するため）
            async for msg in channel.history(limit=50):
                if msg.author == self.bot.user and msg.created_at.date() == now.date():
                    await msg.delete()
                    break

            await channel.send(f"🐶 ミルクシュガーの今日の一言：{message}")

    def load_pet(self):
        try:
            with open("data/pets.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"personality": "ふわふわ"}

def setup(bot):
    bot.add_cog(DailyQuote(bot))
