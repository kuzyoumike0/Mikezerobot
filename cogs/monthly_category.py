import discord
from discord.ext import commands, tasks
import json
import os
import datetime
from zoneinfo import ZoneInfo

from config import GUILD_ID, VC_CHANNEL_IDS

REFERENCE_CHANNEL_KEY = "セッション１"
JST = ZoneInfo("Asia/Tokyo")
MONTHLY_CATEGORY_DATA_PATH = "data/monthly_category.json"
MONTHS_AHEAD = 3


def get_category_name(target_date: datetime.date) -> str:
    return f"{target_date.year}年{target_date.month}月"


def add_months(base_date: datetime.date, months: int) -> datetime.date:
    month_index = base_date.month - 1 + months
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    return datetime.date(year, month, 1)


class MonthlyCategoryCreator(commands.Cog):
    """毎月1日に自動で『MONTHS_AHEADヶ月先』の『○年○月』カテゴリを新設するコグ。
    !createmonthlycategory コマンドで任意の年月を手動作成することも可能。
    """

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.monthly_category_task.start()
        print("[MonthlyCategoryCreator] Cog initialized. 自動タスクを開始しました。")

    def cog_unload(self):
        self.monthly_category_task.cancel()

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
        print(f"[MonthlyCategoryCreator] カテゴリ『{category_name}』を作成しました。")
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

    # ---------------- 手動コマンド ----------------
    @commands.command(name="createmonthlycategory")
    @commands.has_permissions(administrator=True)
    async def createmonthlycategory(self, ctx, year: int = None, month: int = None):
        """
        手動で月別カテゴリを作成する（管理者のみ）。
        使い方:
          !createmonthlycategory          → 今月のカテゴリを作成
          !createmonthlycategory 2026 8   → 2026年8月のカテゴリを作成
        """
        now = datetime.datetime.now(JST)
        if year is None or month is None:
            target_date = now.date()
        else:
            try:
                target_date = datetime.date(year, month, 1)
            except ValueError:
                await ctx.send("年月の指定が正しくありません。例: `!createmonthlycategory 2026 8`")
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
            await ctx.send("年月の指定が正しくありません。例: `!createmonthlycategory 2026 8`")
        else:
            print(f"[ERROR] createmonthlycategory: {error}")
            await ctx.send("エラーが発生しました。")


async def setup(bot):
    await bot.add_cog(MonthlyCategoryCreator(bot))
