import discord
from discord.ext import commands, tasks
import json
import os
import re
import datetime
from zoneinfo import ZoneInfo

from config import GUILD_ID, VC_CHANNEL_IDS, AUDIT_LOG_CHANNEL_ID
from cogs.delete_channel import add_dynamic_allowed_category_id, remove_dynamic_allowed_category_id

REFERENCE_CHANNEL_KEY = "セッション１"
JST = ZoneInfo("Asia/Tokyo")
MONTHLY_CATEGORY_DATA_PATH = "data/monthly_category.json"
MONTHS_AHEAD = 3
MONTHLY_CATEGORY_NAME_PATTERN = re.compile(r"^(\d+)年(\d+)月$")


def get_category_name(target_date: datetime.date) -> str:
    return f"{target_date.year}年{target_date.month}月"


def add_months(base_date: datetime.date, months: int) -> datetime.date:
    month_index = base_date.month - 1 + months
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    return datetime.date(year, month, 1)


class MonthlyCategoryCreator(commands.Cog):
    """毎月1日に自動で『MONTHS_AHEADヶ月先』の『○年○月』カテゴリを新設するコグ。
    !CMC コマンドで任意の年月を手動作成することも可能。
    """

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.monthly_category_task.start()
        self.monthly_category_cleanup_task.start()
        print("[MonthlyCategoryCreator] Cog initialized. 自動タスクを開始しました。")

    def cog_unload(self):
        self.monthly_category_task.cancel()
        self.monthly_category_cleanup_task.cancel()

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

    def _month_key(self, target_date: datetime.date) -> str:
        return f"{target_date.year}-{target_date.month:02d}"

    # ---------------- 位置調整（セッション１の真上に配置） ----------------
    async def position_above_reference(self, guild: discord.Guild, category: discord.CategoryChannel):
        ref_id = VC_CHANNEL_IDS.get(REFERENCE_CHANNEL_KEY)
        if ref_id is None:
            print(f"[MonthlyCategoryCreator] config.VC_CHANNEL_IDSに『{REFERENCE_CHANNEL_KEY}』がありません。")
            return
        ref_channel = guild.get_channel(ref_id)
        if ref_channel is None:
            print(f"[MonthlyCategoryCreator] 基準チャンネル『{REFERENCE_CHANNEL_KEY}』が見つかりません。")
            return
        target_position = ref_channel.category.position if ref_channel.category else ref_channel.position
        try:
            await category.edit(position=target_position)
        except discord.HTTPException as e:
            print(f"[MonthlyCategoryCreator] カテゴリの位置調整に失敗しました: {e}")

    # ---------------- カテゴリ作成本体 ----------------
    async def create_monthly_category(self, guild: discord.Guild, target_date: datetime.date):
        category_name = get_category_name(target_date)
        existing = discord.utils.get(guild.categories, name=category_name)
        if existing:
            return existing, False
        category = await guild.create_category(category_name)
        await self.position_above_reference(guild, category)
        add_dynamic_allowed_category_id(category.id)
        print(f"[MonthlyCategoryCreator] カテゴリ『{category_name}』を作成しました。（削除許可リストにも追加）")
        return category, True

    # ---------------- 自動実行タスク ----------------
    @tasks.loop(time=datetime.time(hour=0, minute=5, tzinfo=JST))
    async def monthly_category_task(self):
        now = datetime.datetime.now(JST)
        if now.day != 1:
            return
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            print("[MonthlyCategoryCreator] GUILD_IDのサーバーが見つかりません。")
            return
        target_date = add_months(now.date(), MONTHS_AHEAD)
        data = self.load_data()
        month_key = self._month_key(target_date)
        if data.get("last_created") == month_key:
            return
        category, created = await self.create_monthly_category(guild, target_date)
        data["last_created"] = month_key
        self.save_data(data)
        if created:
            print(f"[MonthlyCategoryCreator] 自動作成完了（{MONTHS_AHEAD}ヶ月先）: {category.name}")

    @monthly_category_task.before_loop
    async def before_monthly_category_task(self):
        await self.bot.wait_until_ready()
        guild = self.bot.get_guild(GUILD_ID)
        if guild is not None:
            now = datetime.datetime.now(JST)
            target_date = add_months(now.date(), MONTHS_AHEAD)
            await self.create_monthly_category(guild, target_date)

    # ---------------- 自動削除タスク（月初めに一回、当月を過ぎた月別カテゴリを中身ごと削除） ----------------
    @tasks.loop(time=datetime.time(hour=0, minute=15, tzinfo=JST))
    async def monthly_category_cleanup_task(self):
        now = datetime.datetime.now(JST)
        if now.day != 1:
            return
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            print("[MonthlyCategoryCreator] GUILD_IDのサーバーが見つかりません。")
            return
        await self.cleanup_past_categories(guild)

    @monthly_category_cleanup_task.before_loop
    async def before_monthly_category_cleanup_task(self):
        await self.bot.wait_until_ready()

    async def cleanup_past_categories(self, guild: discord.Guild):
        now = datetime.datetime.now(JST).date()

        for category in list(guild.categories):
            match = MONTHLY_CATEGORY_NAME_PATTERN.match(category.name)
            if not match:
                continue

            year, month = int(match.group(1)), int(match.group(2))
            if (year, month) >= (now.year, now.month):
                continue  # まだ当月を過ぎていない

            deleted_channel_names = []
            for channel in list(category.channels):
                try:
                    deleted_channel_names.append(channel.name)
                    await channel.delete(reason="月別カテゴリの自動クリーンアップ（当月経過）")
                except discord.HTTPException as e:
                    print(f"[MonthlyCategoryCreator] チャンネル削除失敗: {channel.name}: {e}")

            try:
                category_name = category.name
                category_id = category.id
                await category.delete(reason="月別カテゴリの自動クリーンアップ（当月経過）")
                remove_dynamic_allowed_category_id(category_id)
                print(f"[MonthlyCategoryCreator] カテゴリ『{category_name}』を自動削除しました。")
                await self.send_cleanup_audit_log(guild, category_name, category_id, deleted_channel_names)
            except discord.HTTPException as e:
                print(f"[MonthlyCategoryCreator] カテゴリ削除失敗: {category.name}: {e}")

    async def send_cleanup_audit_log(self, guild: discord.Guild, category_name: str, category_id: int, channel_names: list):
        log_channel = guild.get_channel(AUDIT_LOG_CHANNEL_ID)
        if log_channel is None:
            return

        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        embed = discord.Embed(
            title="🗑️ 月別カテゴリ自動削除ログ",
            color=discord.Color.red(),
        )
        embed.add_field(name="削除されたカテゴリ", value=f"{category_name} (ID: {category_id})", inline=False)
        embed.add_field(
            name="一緒に削除されたチャンネル",
            value="\n".join(channel_names) if channel_names else "（チャンネルなし）",
            inline=False,
        )
        embed.add_field(name="日時", value=now, inline=False)

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    # ---------------- 手動コマンド ----------------
    @commands.command(name="CMC")
    @commands.has_permissions(administrator=True)
    async def createmonthlycategory(self, ctx, year: int = None, month: int = None):
        """
        手動で月別カテゴリを作成する（管理者のみ）。
        使い方:
          !CMC          → 今月のカテゴリを作成
          !CMC 2026 8   → 2026年8月のカテゴリを作成
        """
        now = datetime.datetime.now(JST)
        if year is None or month is None:
            target_date = now.date()
        else:
            try:
                target_date = datetime.date(year, month, 1)
            except ValueError:
                await ctx.send("年月の指定が正しくありません。例: `!CMC 2026 8`")
                return

        category, created = await self.create_monthly_category(ctx.guild, target_date)
        data = self.load_data()
        data["last_created"] = self._month_key(target_date)
        self.save_data(data)

        if created:
            await ctx.send(f"✅ カテゴリ『{category.name}』を作成しました。")
        else:
            await ctx.send(f"ℹ️ カテゴリ『{category.name}』は既に存在します。")

    @createmonthlycategory.error
    async def createmonthlycategory_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("このコマンドは管理者のみ使用できます。")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("年月の指定が正しくありません。例: `!CMC 2026 8`")
        else:
            print(f"[ERROR] createmonthlycategory: {error}")
            await ctx.send("エラーが発生しました。")


async def setup(bot):
    await bot.add_cog(MonthlyCategoryCreator(bot))
