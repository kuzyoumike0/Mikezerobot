import discord
from discord.ext import commands, tasks
from datetime import datetime
import pytz

from config import DAILY_POST_CHANNEL_ID

class DailyQuote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.jp_tz = pytz.timezone("Asia/Tokyo")
        self.task = self.daily_task.start()

    def cog_unload(self):
        self.task.cancel()

    @tasks.loop(minutes=1)
    async def daily_task(self):
        now = datetime.now(self.jp_tz)
        if now.hour == 10 and now.minute == 0:
            channel = self.bot.get_channel(DAILY_POST_CHANNEL_ID)
            if channel is None:
                return

            day_of_week = now.strftime("%a")  # Mon, Tue, ...
            weekday_map = {
                "Mon": "月",
                "Tue": "火",
                "Wed": "水",
                "Thu": "木",
                "Fri": "金",
                "Sat": "土",
                "Sun": "日"
            }
            day_jp = weekday_map.get(day_of_week, "月")

            quotes = {
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
                "水": {
                    "ふわふわ": ["もうすぐ週の折り返しふわ〜", "中だるみにはお茶を一杯ふわ！"],
                    "キラキラ": ["折り返し地点でキラキラ維持だキラ！"],
                    "カチカチ": ["水のように柔軟に進もうカチ。"],
                    "もちもち": ["水曜日ももちもち元気！もち！"]
                },
                "木": {
                    "ふわふわ": ["あとちょっとで週末ふわ～", "ふわふわ頑張っていこうふわ！"],
                    "キラキラ": ["今日も全力チャージ！キラ！"],
                    "カチカチ": ["後半戦、ペースを崩すな、カチカチ"],
                    "もちもち": ["今こそもっちりパワー！もちもち～！"]
                },
                "金": {
                    "ふわふわ": ["金曜日はごほうびデーふわ？", "週末前に癒やされようふわ〜"],
                    "キラキラ": ["週末目前！もっと輝いて！キラッ！"],
                    "カチカチ": ["仕上げだ、気を抜くな。カチカチでいけ。"],
                    "もちもち": ["もちもち耐えて週末へ！もちっ！"]
                },
                "土": {
                    "ふわふわ": ["今日はお昼寝日和ふわ？", "休日ふわふわタイムふわ〜"],
                    "キラキラ": ["自由な時間を満喫してね！キラ！"],
                    "カチカチ": ["訓練あるのみ。遊びも真剣に、だぞッチ"],
                    "もちもち": ["もちもち全開でリラックスもち～"]
                },
                "日": {
                    "ふわふわ": ["今日もゆっくりしてふわ〜", "癒やしの一日になりますように！ふわふわ！"],
                    "キラキラ": ["明日への準備もキラキラと！キラ！"],
                    "カチカチ": ["英気を養え。明日に備えよ。ッチ"],
                    "もちもち": ["もちもちと未来を見つめて。もちっ！"]
                }
            }

            # TODO: 将来的にユーザー設定で取得可能にする
            personality = "ふわふわ"
            msgs = quotes.get(day_jp, {}).get(personality, ["今日もがんばろう！"])

            await channel.send(f"【ミルクシュガーの今日の一言】\n{msgs[0]}")

    @daily_task.before_loop
    async def before_daily_task(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(DailyQuote(bot))
