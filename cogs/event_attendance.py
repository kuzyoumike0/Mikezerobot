import discord
from discord.ext import commands
import csv
from collections import defaultdict

EVENT_DATA_FILE = "event_data.csv"

REACTION_OPTIONS = {
    "🟡": "朝の部",
    "🟢": "昼の部",
    "🔵": "夜の部",
    "📣": "中締め",
    "❔": "未定"
}

class EventCheckin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.events = {}

    @commands.command(name="set_event")
    async def set_event(self, ctx, year: str, month: str, day: str, *, title: str):
        """イベントを登録して出欠確認メッセージを送信します。"""
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        event_id = f"{date_str}_{title}"

        embed = discord.Embed(
            title=f"{title}",
            description=f"出欠をリアクションで選んでください！\n📅 日付: {date_str}",
            color=discord.Color.blue()
        )

        for emoji, label in REACTION_OPTIONS.items():
            embed.add_field(name=f"{emoji} {label}", value="0人", inline=False)

        message = await ctx.send(embed=embed)

        self.events[message.id] = {
            "event_id": event_id,
            "title": title,
            "date": date_str,
            "message": message,
            "reactions": defaultdict(list)
        }

        for emoji in REACTION_OPTIONS:
            await message.add_reaction(emoji)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id not in self.events or payload.user_id == self.bot.user.id:
            return
        if payload.emoji.name not in REACTION_OPTIONS:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        member = guild.get_member(payload.user_id)
        if member is None or member.bot:
            return

        event = self.events[payload.message_id]
        label = REACTION_OPTIONS[payload.emoji.name]

        # 他のリアクションを除去（1ユーザー1リアクション制）
        for other_label, users in event["reactions"].items():
            if member.display_name in users and other_label != label:
                users.remove(member.display_name)

        if member.display_name not in event["reactions"][label]:
            event["reactions"][label].append(member.display_name)

        await self.update_embed(payload.message_id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id not in self.events:
            return
        if payload.emoji.name not in REACTION_OPTIONS:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        member = guild.get_member(payload.user_id)
        if member is None or member.bot:
            return

        event = self.events[payload.message_id]
        label = REACTION_OPTIONS[payload.emoji.name]
        if member.display_name in event["reactions"][label]:
            event["reactions"][label].remove(member.display_name)

        await self.update_embed(payload.message_id)

    async def update_embed(self, message_id):
        event = self.events[message_id]
        message = event["message"]
        embed = discord.Embed(
            title=event["title"],
            description=f"出欠をリアクションで選んでください！\n📅 日付: {event['date']}",
            color=discord.Color.green()
        )
        for emoji, label in REACTION_OPTIONS.items():
            count = len(event["reactions"][label])
            embed.add_field(name=f"{emoji} {label}", value=f"{count}人", inline=False)
        await message.edit(embed=embed)

    @commands.command(name="export_csv")
    async def export_csv(self, ctx):
        """現在のイベント出欠情報をCSVとしてエクスポートします。"""
        if not self.events:
            await ctx.send("⚠️ エクスポートするイベントがありません。")
            return

        with open(EVENT_DATA_FILE, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["イベントID", "日付", "部", "ニックネーム"])
            for event in self.events.values():
                for label, names in event["reactions"].items():
                    for name in names:
                        writer.writerow([event["event_id"], event["date"], label, name])

        await ctx.send("✅ 出欠情報をCSVに書き出しました。", file=discord.File(EVENT_DATA_FILE))

def setup(bot):
    bot.add_cog(EventCheckin(bot))
