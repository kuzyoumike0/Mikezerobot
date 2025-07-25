import discord
from discord.ext import commands, tasks
import datetime
import pytz
import json
import os
import random

from config import DAILY_QUOTE_CHANNEL_ID  # config.pyからチャンネルIDを読み込み

PET_DATA_PATH = "data/pets.json"
POST_LOG_PATH = "data/daily_quote_log.json"

quotes = {
    "ふわふわ": {
        "月": [
            "今週もゆっくり始めようふわ～",
            "無理せずふんわりいけばいいふわ～"
        ],
        "火": [
            "火曜日ってなんか眠いふわ…",
            "のんびり火曜日、ちょっと休んでもいいんじゃないかふわ？"
        ],
        "水": [
            "もうすぐ週の折り返しふわ〜",
            "中だるみにはお茶を一杯ふわ！"
        ],
        "木": [
            "あとちょっとで週末ふわ～",
            "ふわふわ頑張っていこうふわ！"
        ],
        "金": [
            "金曜日はごほうびデーふわ？",
            "週末前に癒やされようふわ〜"
        ],
        "土": [
            "今日はお昼寝日和ふわ？",
            "休日ふわふわタイムふわ〜"
        ],
        "日": [
            "今日もゆっくりしてふわ〜",
            "癒やしの一日になりますように！ふわふわ！"
        ]
    },
    "キラキラ": {
        "月": [
            "月曜から全開モードキラ！",
            "輝く一週間のスタートキラ！"
        ],
        "火": [
            "今日もチャンスに満ちてるキラ！",
            "輝きを忘れずに！キラ"
        ],
        "水": [
            "折り返し地点でキラキラ維持だキラ！"
        ],
        "木": [
            "今日も全力チャージ！キラ！"
        ],
        "金": [
            "週末目前！もっと輝いて！キラッ！"
        ],
        "土": [
            "自由な時間を満喫してね！キラ！"
        ],
        "日": [
            "明日への準備もキラキラと！キラ！"
        ]
    },
    "カチカチ": {
        "月": [
            "さあ任務開始だチ。気を引き締めろッチ！"
        ],
        "火": [
            "計画通りに進めようッチ。",
            "火は熱いが冷静にッチ。"
        ],
        "水": [
            "水のように柔軟に進もうカチ。"
        ],
        "木": [
            "後半戦、ペースを崩すな、カチカチ"
        ],
        "金": [
            "仕上げだ、気を抜くな。カチカチでいけ。"
        ],
        "土": [
            "訓練あるのみ。遊びも真剣に、だぞッチ"
        ],
        "日": [
            "英気を養え。明日に備えよ。ッチ"
        ]
    },
    "もちもち": {
        "月": [
            "のび〜っとストレッチして、がんばろ！もちもち！"
        ],
        "火": [
            "もっちり集中デーだよ！もちもち～！"
        ],
        "水": [
            "水曜日ももちもち元気！もち！"
        ],
        "木": [
            "今こそもっちりパワー！もちもち～！"
        ],
        "金": [
            "もちもち耐えて週末へ！もちっ！"
        ],
        "土": [
            "もちもち全開でリラックスもち～"
        ],
        "日": [
            "もちもちと未来を見つめて。もちっ！"
        ]
    }
}

def load_pet_data():
    if not os.path.exists(PET_DATA_PATH):
        return {"personality": "ふわふわ", "mood": 50}
    with open(PET_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_post_log():
    if not os.path.exists(POST_LOG_PATH):
        return {}
    with open(POST_LOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_post_log(log):
    with open(POST_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def get_japanese_weekday():
    jst = pytz.timezone("Asia/Tokyo")
    now = datetime.datetime.now(jst)
    weekdays = ["日", "月", "火", "水", "木", "金", "土"]
    return weekdays[now.weekday()]

class DailyQuote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_task.start()

    def cog_unload(self):
        self.daily_task.cancel()

    @tasks.loop(minutes=30)
    async def daily_task(self):
        jst = pytz.timezone("Asia/Tokyo")
        now = datetime.datetime.now(jst)
        target_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
        if now < target_time:
            return

        post_log = load_post_log()
        last_post_str = post_log.get("last_post_date", "")
        if last_post_str == now.strftime("%Y-%m-%d"):
            return

        channel = self.bot.get_channel(DAILY_QUOTE_CHANNEL_ID)
        if not channel:
            print("指定されたチャンネルが見つかりません。")
            return

        pet_data = load_pet_data()
        personality = pet_data.get("personality", "ふわふわ")
        day = get_japanese_weekday()

        msg_list = quotes.get(personality, {}).get(day, ["今日もがんばろう！"])
        message = random.choice(msg_list)

        try:
            await channel.send(f"🐾 ミルクシュガーの今日の一言 🐾\n{message}")
            post_log["last_post_date"] = now.strftime("%Y-%m-%d")
            save_post_log(post_log)
        except Exception as e:
            print(f"投稿エラー: {e}")

    @daily_task.before_loop
    async def before_daily_task(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(DailyQuote(bot))
