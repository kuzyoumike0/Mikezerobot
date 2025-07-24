import discord
from discord.ext import commands
import csv
import os
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

    @commands.command(name="!set_event")
    async def set_event(self, ctx, year: str, date: str, event_name: str, title: str):
        event_id = f"{year}-{date}_{event_name}_{title}"
        embed = discord.Embed(
            title=f"{event_name} - {title}",
            description=f"出欠をリアクションで選んでください！\n日付: {year}-{date}",
            color=discord.Color.blue()
        )
        for emoji, label in REACTION_OPTIONS.items():
            embed.add_field(name=f"{emoji} {label}", value="0人", inline=False)

        message = await ctx.send(embed=embed)

        self.events[message.id] = {
            "event_id": event_id,
            "title": f"{event_name} - {title}",
            "date": f"{year}-{date}",
            "message": message,
            "reactions": defaultdict(list)
        }

        for emoji in REACTION_OPTIONS:
            await message.add_reaction(emoji)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id not in self.events:
            return
        if payload.emoji.name not in REACTION_OPTIONS:
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member is None or member.bot:
            return

        event = self.events[payload.message_id]
        label = REACTION_OPTIONS[payload.emoji.name]
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
            description=f"出欠をリアクションで選んでください！\n日付: {event['date']}",
            color=discord.Color.green()
        )
        for emoji, label in REACTION_OPTIONS.items():
            count = len(event["reactions"][label])
            embed.add_field(name=f"{emoji} {label}", value=f"{count}人", inline=False)
        await message.edit(embed=embed)

    @commands.command(name="!export_csv")
    async def export_csv(self, ctx):
        if not self.events:
            await ctx.send("エクスポートするイベントがありません。")
            return

        with open(EVENT_DATA_FILE, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["イベントID", "日付", "部", "ニックネーム"])

            for event in self.events.values():
                for label, names in event["reactions"].items():
                    for name in names:
                        writer.writerow([event["event_id"], event["date"], label, name])

        await ctx.send(file=discord.File(EVENT_DATA_FILE))

def setup(bot):
    bot.add_cog(EventCheckin(bot))
