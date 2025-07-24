import discord
from discord.ext import commands
import csv
from collections import defaultdict
import os

EVENT_DATA_DIR = "attendance_records"  # CSV保存フォルダ

REACTION_OPTIONS = {
    "🌅": "朝の部",
    "☀️": "昼の部",
    "🌙": "夜の部",
    "📣": "中締め"
}

class EventCheckin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.events = {}  # message.id : eventデータ

        if not os.path.exists(EVENT_DATA_DIR):
            os.makedirs(EVENT_DATA_DIR)

    @commands.command(name="set_event")
    async def set_event(self, ctx, year: str, month: str, day: str, *, title: str):
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        event_id = f"{date_str}_{title.replace(' ', '_')}"

        embed = discord.Embed(
            title=title,
            description=f"出欠をリアクションで選択してください！\n日付: {date_str}",
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
        if payload.user_id == self.bot.user.id:
            return

        if payload.message_id not in self.events:
            return

        emoji_str = str(payload.emoji)
        if emoji_str not in REACTION_OPTIONS:
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        event = self.events[payload.message_id]
        label = REACTION_OPTIONS[emoji_str]

        if member.display_name not in event["reactions"][label]:
            event["reactions"][label].append(member.display_name)

        await self.update_embed(payload.message_id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id not in self.events:
            return

        emoji_str = str(payload.emoji)
        if emoji_str not in REACTION_OPTIONS:
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        event = self.events[payload.message_id]
        label = REACTION_OPTIONS[emoji_str]

        if member.display_name in event["reactions"][label]:
            event["reactions"][label].remove(member.display_name)

        await self.update_embed(payload.message_id)

    async def update_embed(self, message_id):
        event = self.events[message_id]
        message = event["message"]

        embed = discord.Embed(
            title=event["title"],
            description=f"出欠をリアクションで選択してください！\n日付: {event['date']}",
            color=discord.Color.green()
        )
        for emoji, label in REACTION_OPTIONS.items():
            count = len(event["reactions"][label])
            embed.add_field(name=f"{emoji} {label}", value=f"{count}人", inline=False)

        await message.edit(embed=embed)

    @commands.command(name="export_csv")
    async def export_csv(self, ctx, *, title: str):
        # titleでイベントを検索
        matched_events = [e for e in self.events.values() if e["title"] == title]

        if not matched_events:
            await ctx.send(f"タイトル「{title}」のイベントが見つかりません。")
            return

        # 複数ヒットする可能性があるため、最初のものを使う
        event = matched_events[0]

        filename = os.path.join(EVENT_DATA_DIR, f"{event['event_id']}.csv")
        with open(filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["イベント名", "日付", "参加区分", "ニックネーム"])

            for label, names in event["reactions"].items():
                for name in names:
                    writer.writerow([event["title"], event["date"], label, name])

        await ctx.send(file=discord.File(filename))

def setup(bot):
    bot.add_cog(EventCheckin(bot))
