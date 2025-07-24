import discord
from discord.ext import commands
import csv
import io
import datetime

class EventAttendance(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.events = {}  # event_id: {datetime, message_id, channel_id, reactions: {emoji: set(user_ids)}}
        self.event_counter = 0

        # 出欠用絵文字
        self.REACTIONS = {
            "✅": "参加",
            "❌": "不参加",
            "❓": "未定"
        }

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} Cog is ready.")

    # テキストコマンド：!set_event
    @commands.command(name="set_event")
    async def set_event(self, ctx: commands.Context, *, datetime_str: str):
        try:
            event_dt = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            await ctx.send("日時の形式が正しくありません。YYYY-MM-DD HH:MM の形式で入力してください。")
            return

        self.event_counter += 1
        event_id = self.event_counter

        msg = await ctx.send(
            f"【イベントID {event_id}】\nイベント日時: {event_dt.strftime('%Y-%m-%d %H:%M')}\n"
            f"以下の絵文字で出欠をリアクションしてください。\n" +
            "\n".join(f"{emoji}: {desc}" for emoji, desc in self.REACTIONS.items())
        )
        for emoji in self.REACTIONS.keys():
            await msg.add_reaction(emoji)

        self.events[event_id] = {
            "datetime": event_dt,
            "message_id": msg.id,
            "channel_id": ctx.channel.id,
            "reactions": {emoji: set() for emoji in self.REACTIONS.keys()}
        }

        await ctx.send(f"イベントID {event_id} を登録しました。")

    # テキストコマンド：!export_csv
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

        await ctx.send(f"イベントID {event_id} の出欠結果CSVです。", file=file)

    # テキストコマンド：!help_event
    @commands.command(name="help_event")
    async def help_event(self, ctx: commands.Context):
        embed = discord.Embed(
            title="📋 イベント出欠確認Bot Help",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="!set_event <YYYY-MM-DD HH:MM>",
            value="イベントの日付と時間を登録します。例: `!set_event 2025-08-01 19:30`",
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

    # リアクション追加イベント
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

    # リアクション削除イベント
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
