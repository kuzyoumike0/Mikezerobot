# cogs/daily_quote.py

import discord
from discord.ext import commands, tasks
import datetime
import json
import random

from config import DAILY_POST_CHANNEL_ID

PET_DATA_PATH = "data/pets.json"

# 曜日別 × 性格別のメッセージ
DAILY_QUOTES = {
    "月": {
        "まるまる": ["今週もゆっくり始めようね！", "無理せずふんわりいこう〜"],
        "キラキラ": ["月曜から全開モード！", "輝く一週間のスタートだよ！"],
        "カチカチ": ["さあ任務開始だ。気を引き締めろ！"],
        "もちもち": ["のび〜っとストレッチして、がんばろ！"]
    },
    "火": {
        "まるまる": ["火曜日ってなんか眠いよね…", "のんびり火曜日、ちょっと休もう"],
        "キラキラ": ["今日もチャンスに満ちてる！", "輝きを忘れずに！"],
        "カチカチ": ["計画通りに進めよう。", "火は熱いが冷静に。"],
        "もちもち": ["もっちり集中デーだよ！"]
    },
    "水": {
        "まるまる": ["もうすぐ週の折り返し〜", "中だるみにはお茶を一杯"],
        "キラキラ": ["折り返し地点でキラキラ維持！"],
        "カチカチ": ["水のように柔軟に進もう。"],
        "もちもち": ["水曜日ももちもち元気！"]
    },
    "木": {
        "まるまる": ["あとちょっとで週末だね〜", "ふわふわ頑張っていこう"],
        "キラキラ": ["今日も全力チャージ！"],
        "カチカチ": ["後半戦、ペースを崩すな。"],
        "もちもち": ["今こそもっちりパワー！"]
    },
    "金": {
        "まるまる": ["金曜日はごほうびデー？", "週末前に癒やされよう〜"],
        "キラキラ": ["週末目前！もっと輝いて！"],
        "カチカチ": ["仕上げだ、気を抜くな。"],
        "もちもち": ["もちもち耐えて週末へ！"]
    },
    "土": {
        "まるまる": ["今日はお昼寝日和かも？", "休日ふわふわタイム〜"],
        "キラキラ": ["自由な時間を満喫してね！"],
        "カチカチ": ["訓練あるのみ。遊びも真剣に。"],
        "もちもち": ["もちもち全開でリラックス〜"]
    },
    "日": {
        "まるまる": ["今日もゆっくりしてね〜", "癒やしの一日になりますように！"],
        "キラキラ": ["明日への準備もキラキラと！"],
        "カチカチ": ["英気を養え。明日に備えよ。"],
        "もちもち": ["もちもちと未来を見つめて。"]
    }
}


class DailyQuote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_quote_task.start()

    def cog_unload(self):
        self.daily_quote_task.cancel()

    def get_day_of_week(self):
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        return "月火水木金土日"[now.weekday()]

    def load_pet_data(self):
        try:
            with open(PET_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def get_personality_by_user(self, user_id: str):
        pets = self.load_pet_data()
        pet = pets.get(user_id)
        if not pet:
            return "まるまる"  # デフォルト性格
        return pet.get("personality", "まるまる")

    def get_daily_message(self, personality: str, day: str):
        messages = DAILY_QUOTES.get(day, {}).get(personality, ["今日もがんばろう！"])
        return random.choice(messages)

    @tasks.loop(time=datetime.time(hour=10, tzinfo=datetime.timezone(datetime.timedelta(hours=9))))
    async def daily_quote_task(self):
        channel = self.bot.get_channel(DAILY_POST_CHANNEL_ID)
        if not channel:
            return

        day = self.get_day_of_week()

        # botのサーバーメンバー一覧からユーザーごとに投稿
        for member in channel.guild.members:
            if member.bot:
                continue

            personality = self.get_personality_by_user(str(member.id))
            message = self.get_daily_message(personality, day)

            embed = discord.Embed(
                title=f"☀️ {member.display_name} への今日のひとこと",
                description=f"性格：**{personality}**\n📅 **{day}曜日**\n📝 {message}",
                color=discord.Color.green()
            )
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                continue  # チャンネル投稿権限がない場合はスキップ


def setup(bot):
    bot.add_cog(DailyQuote(bot))
