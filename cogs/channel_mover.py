import discord
from discord.ext import commands
import json
import os
import re
import datetime
from zoneinfo import ZoneInfo

from config import CATEGORY_ID, AUDIT_LOG_CHANNEL_ID

JST = ZoneInfo("Asia/Tokyo")
MONTHLY_CATEGORY_DATA_PATH = "data/monthly_category.json"

GM_ROLE_NAME = "GM"

MONTHLY_CATEGORY_NAME_PATTERN = re.compile(r"^\d+年\d+月$")
EVENT_MONTH_CATEGORY_NAME_PATTERN = re.compile(r"^\d+月開催卓?$")


def get_category_name(target_date: datetime.date) -> str:
    return f"{target_date.year}年{target_date.month}月"


class NotGMOrAdmin(commands.CheckFailure):
    pass


def is_gm_or_admin():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        if discord.utils.get(ctx.author.roles, name=GM_ROLE_NAME):
            return True
        raise NotGMOrAdmin("GMロールまたは管理者のみ使用できます。")
    return commands.check(predicate)


def is_allowed_category(category: discord.CategoryChannel) -> bool:
    if category is None:
        return False
    if category.id == CATEGORY_ID:
        return True
    if MONTHLY_CATEGORY_NAME_PATTERN.match(category.name):
        return True
    if EVENT_MONTH_CATEGORY_NAME_PATTERN.match(category.name):
        return True
    return False


class ChannelMover(commands.Cog):
    """チャンネルを月別カテゴリへ移動し、開催日順にソートするコグ。
    コマンド: !m2m（移動）、!SD（日付登録のみ）、!RES（全体再ソート）
    """

    def __init__(self, bot):
        self.bot = bot

    # ---------------- 永続化 ----------------
    def load_data(self) -> dict:
        if not os.path.exists(MONTHLY_CATEGORY_DATA_PATH):
            return {"last_created": None, "channel_dates": {}}
        try:
            with open(MONTHLY_CATEGORY_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("channel_dates", {})
                return data
        except json.JSONDecodeError:
            return {"last_created": None, "channel_dates": {}}

    def save_data(self, data: dict):
        os.makedirs(os.path.dirname(MONTHLY_CATEGORY_DATA_PATH), exist_ok=True)
        with open(MONTHLY_CATEGORY_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def save_channel_date(self, channel_id: int, target_date: datetime.date):
        data = self.load_data()
        data["channel_dates"][str(channel_id)] = target_date.isoformat()
        self.save_data(data)

    # ---------------- 全体再ソート ----------------
    async def full_resort_category(self, category: discord.CategoryChannel):
        data = self.load_data()
        channel_dates = data.get("channel_dates", {})
        unrecognized_channels = []

        def sort_key(ch):
            date_str = channel_dates.get(str(ch.id))
            if date_str:
                try:
                    return (0, datetime.date.fromisoformat(date_str), ch.position)
                except ValueError:
                    pass
            unrecognized_channels.append(ch.name)
            return (1, datetime.date.max, ch.position)

        async def reorder(channels):
            if len(channels) <= 1:
                return
            ordered = sorted(channels, key=sort_key)
            for ch in reversed(ordered):
                try:
                    await ch.move(beginning=True, category=category, sync_permissions=False)
                except discord.HTTPException as e:
                    print(f"[ChannelMover] 再ソート中にエラー（{ch.name}）: {e}")

        await reorder(category.text_channels)
        await reorder(category.voice_channels)

        if unrecognized_channels:
            await self.send_unrecognized_date_log(category, unrecognized_channels)

    async def send_unrecognized_date_log(self, category: discord.CategoryChannel, channel_names: list):
        log_channel = category.guild.get_channel(AUDIT_LOG_CHANNEL_ID)
        if log_channel is None:
            return

        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        embed = discord.Embed(
            title="⚠️ 開催日未認識チャンネルログ",
            description=f"カテゴリ『{category.name}』のソート時、開催日（月日）を認識できなかったチャンネルがあります。",
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="対象チャンネル",
            value="\n".join(f"- {name}" for name in channel_names),
            inline=False,
        )
        embed.add_field(name="日時", value=now, inline=False)

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    # ---------------- !m2m ----------------
    @commands.command(name="m2m")
    @is_gm_or_admin()
    async def m2m(self, ctx, date_str: str):
        """
        チャンネルを指定した月日のカテゴリへ移動し、開催日を記録してソートする（GM or 管理者のみ）。
        使い方: !m2m 0630（6月30日） / !m2m r（固定カテゴリへ移動）
        """
        if not is_allowed_category(ctx.channel.category):
            await ctx.send("このチャンネルではこのコマンドは使えません。")
            return

        s = date_str.strip()

        if s.lower() == "r":
            category = ctx.guild.get_channel(CATEGORY_ID)
            if category is None or not isinstance(category, discord.CategoryChannel):
                await ctx.send(f"カテゴリが見つかりません（ID: {CATEGORY_ID}）。")
                return
            try:
                await ctx.channel.edit(category=category, sync_permissions=False)
            except discord.HTTPException as e:
                print(f"[ERROR] m2m r: {e}")
                await ctx.send("チャンネルの移動に失敗しました。Botの権限を確認してください。")
                return
            await ctx.send(f"✅ このチャンネルを『{category.name}』に移動しました。")
            return

        if len(s) != 4 or not s.isdigit():
            await ctx.send("入力形式が正しくありません。例: `!m2m 0630`（6月30日）または `!m2m r`")
            return

        month = int(s[0:2])
        day = int(s[2:4])
        now = datetime.datetime.now(JST)
        year = now.year if month >= now.month else now.year + 1

        try:
            target_date = datetime.date(year, month, day)
        except ValueError:
            await ctx.send("存在しない日付です。確認してください。")
            return

        category_name = get_category_name(target_date)
        category = discord.utils.get(ctx.guild.categories, name=category_name)
        if category is None:
            await ctx.send(
                f"カテゴリ『{category_name}』が見つかりません。"
                f"管理人にご連絡ください。"
            )
            return

        try:
            await ctx.channel.edit(category=category, sync_permissions=False)
        except discord.HTTPException as e:
            print(f"[ERROR] m2m: {e}")
            await ctx.send("チャンネルの移動に失敗しました。Botの権限を確認してください。")
            return

        self.save_channel_date(ctx.channel.id, target_date)
        await self.full_resort_category(category)
        await ctx.send(f"✅ このチャンネルを『{category_name}』に移動しました。")

    @m2m.error
    async def m2m_error(self, ctx, error):
        if isinstance(error, NotGMOrAdmin):
            await ctx.send("このコマンドはGMロールまたは管理者のみ使用できます。")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("月日を指定してください。例: `!m2m 0630` または `!m2m r`")
        else:
            print(f"[ERROR] m2m: {error}")
            await ctx.send("エラーが発生しました。")

    # ---------------- !SD ----------------
    @commands.command(name="SD")
    @is_gm_or_admin()
    async def set_date(self, ctx, date_str: str):
        """
        移動なしで開催日だけ登録してカテゴリ内をソートする（GM or 管理者のみ）。
        使い方: !SD 0630（6月30日）
        """
        if not is_allowed_category(ctx.channel.category):
            await ctx.send("このチャンネルではこのコマンドは使えません。")
            return

        s = date_str.strip()
        if len(s) != 4 or not s.isdigit():
            await ctx.send("入力形式が正しくありません。例: `!SD 0630`（6月30日）")
            return

        month = int(s[0:2])
        day = int(s[2:4])
        now = datetime.datetime.now(JST)
        year = now.year if month >= now.month else now.year + 1

        try:
            target_date = datetime.date(year, month, day)
        except ValueError:
            await ctx.send("存在しない日付です。確認してください。")
            return

        self.save_channel_date(ctx.channel.id, target_date)
        await self.full_resort_category(ctx.channel.category)
        await ctx.send(
            f"✅ このチャンネルの開催日を {target_date.strftime('%Y年%m月%d日')} に登録し、"
            f"カテゴリ内を並び替えました。"
        )

    @set_date.error
    async def set_date_error(self, ctx, error):
        if isinstance(error, NotGMOrAdmin):
            await ctx.send("このコマンドはGMロールまたは管理者のみ使用できます。")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("月日を指定してください。例: `!SD 0630`")
        else:
            print(f"[ERROR] SD: {error}")
            await ctx.send("エラーが発生しました。")

    # ---------------- !RES ----------------
    @commands.command(name="RES")
    @is_gm_or_admin()
    async def resort(self, ctx):
        """
        カテゴリ全体を記録済みの開催日でゼロから並び替える（GM or 管理者のみ）。
        使い方: !RES
        """
        category = ctx.channel.category
        if not is_allowed_category(category):
            await ctx.send("このチャンネルではこのコマンドは使えません。")
            return

        await ctx.send(f"🔄 『{category.name}』を再ソートしています…")
        await self.full_resort_category(category)
        await ctx.send(f"✅ 『{category.name}』の並び替えが完了しました。")

    @resort.error
    async def resort_error(self, ctx, error):
        if isinstance(error, NotGMOrAdmin):
            await ctx.send("このコマンドはGMロールまたは管理者のみ使用できます。")
        else:
            print(f"[ERROR] RES: {error}")
            await ctx.send("エラーが発生しました。")


async def setup(bot):
    await bot.add_cog(ChannelMover(bot))
