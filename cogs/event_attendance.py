import discord
from discord.ext import commands
import csv
import io
import datetime

class EventAttendance(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.events = {}  # event_id: {date, message_id, channel_id, event_name, title, reactions: {emoji: set(user_ids)}}
        self.event_counter = 0

        self.REACTIONS = {
            "✅": "参加",
            "❌": "不参加",
            "❓": "未定"
        }

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} Cog is ready.")

    @commands.command(name="set_event")
    async def set_event(self, ctx: commands.Context, year: str, date: str, event_name: str, title: str):
        """
        使い方例:
        !set_event 2025 08-01 夏祭り 花火大会
        """

        date_str = f"{year}-{date}"
        try:
            event_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            await ctx.send("日付の形式が正しくありません。\n年: YYYY, 日付: MM-DD の形式で入力してください。\n例: !set_event 2025 08-01 夏祭り 花火大会")
            return

        self.event_counter += 1
        event_id = self.event_counter

        msg = await ctx.send(
            f"【イベントID {event_id}】\n"
            f"イベント名: {event_name}\n"
            f"タイトル: {title}\n"
            f"日付: {event_date.strftime('%Y-%m-%d')}\n"
            f"以下の絵文字で出欠をリアクションしてください。\n" +
            "\n".join(f"{emoji}: {desc}" for emoji, desc in self.REACTIONS.items())
        )
        for emoji in self.REACTIONS.keys():
            await msg.add_reaction(emoji)

        self.events[event_id] = {
            "date": event_date,
            "message_id": msg.id,
            "channel_id": ctx.channel.id,
            "event_name": event_name,
            "title": title,
            "reactions": {emoji: set() for emoji in self.REACTIONS.keys()}
        }

        await ctx.send(f"イベントID {event_id} を登録しました。")

    @commands.command(name="export_csv")
    async def export_csv(self, ctx: commands.Context, event_id: int):
        if event_id not in self.events:
            await ctx.send("指定されたイベントIDは存在しません。")
            return

        event_data = self.events[event_id]
        channel = self.bot.get_channel(event_data["channel_id"])
        if channel is None:
            await ctx.send("イベントのチャンネルが見つかりません。")
            return

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ニックネーム", "出欠"])

        for emoji, user_ids in event_data["reactions"].items():
            for user_id in user_ids:
                member = channel.guild.get_member(user_id)
                name = member.display_name if member else f"ユーザーID:{user_id}"
                writer.writerow([name, self.REACTIONS[emoji]])

        output.seek(0)
        file = discord.File(fp=io.BytesIO(output.read().encode()), filename=f"event_{event_id}_attendance.csv")

        await ctx.send(f"イベントID {event_id} ({event_data['event_name']} - {event_data['title']}) の出欠結果CSVです。", file=file)

    @commands.command(name="help_event")
    async def help_event(self, ctx: commands.Context):
        embed = discord.Embed(
            title="📋 イベント出欠確認Bot Help",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="!set_event <年 YYYY> <日付 MM-DD> <イベント名> <タイトル>",
            value="例: `!set_event 2025 08-01 夏祭り 花火大会`\nイベントを登録します。",
            inline=False
        )
        embed.add_field(
            name="!export_csv <イベントID>",
            value="指定したイベントの出欠結果をCSV形式で出力します。",
            inline=False
        )
        embed.add_field(
            name="出欠リアクション",
            value="✅ 参加\n❌ 不参加\n❓ 未定\nイベントメッセージのリアクションで出欠を登録してください。",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        for event_id, event_data in self.events.items():
            if payload.message_id == event_data["message_id"]:
                emoji = str(payload.emoji)
                if emoji in self.REACTIONS:
                    event_data["reactions"][emoji].add(payload.user_id)
                break

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        for event_id, event_data in self.events.items():
            if payload.message_id == event_data["message_id"]:
                emoji = str(payload.emoji)
                if emoji in self.REACTIONS:
                    event_data["reactions"][emoji].discard(payload.user_id)
                break

async def setup(bot: commands.Bot):
    await bot.add_cog(EventAttendance(bot))
