import discord
from discord.ext import commands, tasks
import json
import os
import re
import asyncio
import datetime
from zoneinfo import ZoneInfo

from config import GUILD_ID, VC_CHANNEL_IDS, CATEGORY_ID

# 新カテゴリをこのチャンネルの真上に配置する
REFERENCE_CHANNEL_KEY = "セッション１"

JST = ZoneInfo("Asia/Tokyo")
MONTHLY_CATEGORY_DATA_PATH = "data/monthly_category.json"

# 自動作成は「何ヶ月先」のカテゴリを作るか（例: 3なら7月に11月分を作る）
MONTHS_AHEAD = 3

# !m2m2 を使えるロール名（これ or 管理者のみ）
GM_ROLE_NAME = "GM"

# 卓ログを送るチャンネルID
LOG_CHANNEL_ID = 1518542529589415956

# このコグが作るカテゴリ名（「2026年7月」など）にマッチする正規表現
MONTHLY_CATEGORY_NAME_PATTERN = re.compile(r"^\d+年\d+月$")

# 既存の「6月開催卓」「7月開催」のような開催月カテゴリにマッチする正規表現
EVENT_MONTH_CATEGORY_NAME_PATTERN = re.compile(r"^\d+月開催卓?$")


def get_category_name(target_date: datetime.date) -> str:
    """対象の年月から「2026年7月」形式のカテゴリ名を作る"""
    return f"{target_date.year}年{target_date.month}月"


def parse_time(time_str: str) -> tuple[int, int]:
    """
    時分文字列を (hour, minute) に変換する。
    3桁: 930  → (9, 30)
    4桁: 1800 → (18, 0)
    """
    if len(time_str) == 3:
        return int(time_str[0]), int(time_str[1:3])
    elif len(time_str) == 4:
        return int(time_str[0:2]), int(time_str[2:4])
    raise ValueError("時分は3〜4桁で入力してください。例: 930 または 1800")


def add_months(base_date: datetime.date, months: int) -> datetime.date:
    """base_date の月にmonthsヶ月を加算した年月（1日付）を返す（標準ライブラリのみで計算）"""
    month_index = base_date.month - 1 + months
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    return datetime.date(year, month, 1)


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
    """m2m2を使ってよいチャンネルかどうか
    （卓用ch作成カテゴリ1 / 月別カテゴリ / ○月開催卓カテゴリ 配下のみ）"""
    if category is None:
        return False
    if category.id == CATEGORY_ID:
        return True
    if MONTHLY_CATEGORY_NAME_PATTERN.match(category.name):
        return True
    if EVENT_MONTH_CATEGORY_NAME_PATTERN.match(category.name):
        return True
    return False


class MonthlyCategory(commands.Cog):
    """毎月1日に自動で『MONTHS_AHEADヶ月先』の『○年○月』カテゴリを新設するコグ。
    !createmonthlycategory コマンドで任意の年月を手動作成することも可能。
    """

    def __init__(self, bot):
        self.bot = bot
        self._pending_reminders: list[asyncio.Task] = []

    async def cog_load(self):
        self.monthly_category_task.start()
        print("[MonthlyCategory] Cog initialized. 自動タスクを開始しました。")

    def cog_unload(self):
        self.monthly_category_task.cancel()

    # ---------------- 永続化（重複作成防止用） ----------------
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
        """!m2m2で指定された開催日（月/日→年月日）をチャンネルごとに保存する"""
        data = self.load_data()
        channel_dates = data.get("channel_dates", {})
        channel_dates[str(channel_id)] = target_date.isoformat()
        data["channel_dates"] = channel_dates
        self.save_data(data)

    def get_channel_date(self, channel_id: int):
        data = self.load_data()
        date_str = data.get("channel_dates", {}).get(str(channel_id))
        if not date_str:
            return None
        try:
            return datetime.date.fromisoformat(date_str)
        except ValueError:
            return None

    # ---------------- カテゴリ内を開催日順に並び替え ----------------
    async def sort_category_by_date(self, category: discord.CategoryChannel):
        """カテゴリ内のチャンネルを、保存済みの開催日（古い→新しい）順に並び替える。
        開催日が未登録のチャンネルは末尾（元の並び順を維持）にする。
        """
        data = self.load_data()
        channel_dates = data.get("channel_dates", {})

        def sort_key(ch):
            date_str = channel_dates.get(str(ch.id))
            if date_str:
                try:
                    return (0, datetime.date.fromisoformat(date_str), ch.position)
                except ValueError:
                    pass
            return (1, datetime.date.max, ch.position)

        async def reorder(channels):
            if not channels:
                return
            ordered = sorted(channels, key=sort_key)
            # 先頭チャンネルをカテゴリの一番上に移動
            try:
                await ordered[0].move(
                    beginning=True, category=category, sync_permissions=False
                )
            except discord.HTTPException as e:
                print(f"[MonthlyCategory] 先頭チャンネルの移動に失敗しました（{ordered[0].name}）: {e}")
                return
            # 2番目以降を直前のチャンネルの後ろに順に移動
            for i in range(1, len(ordered)):
                try:
                    await ordered[i].move(
                        after=ordered[i - 1], category=category, sync_permissions=False
                    )
                except discord.HTTPException as e:
                    print(f"[MonthlyCategory] チャンネル並び替えに失敗しました（{ordered[i].name}）: {e}")

        await reorder(category.text_channels)
        await reorder(category.voice_channels)

    # ---------------- 位置調整（『セッション１』の真上に配置） ----------------
    async def position_above_reference(self, guild: discord.Guild, category: discord.CategoryChannel):
        ref_id = VC_CHANNEL_IDS.get(REFERENCE_CHANNEL_KEY)
        if ref_id is None:
            print(f"[MonthlyCategory] config.VC_CHANNEL_IDSに『{REFERENCE_CHANNEL_KEY}』がありません。位置調整をスキップします。")
            return

        ref_channel = guild.get_channel(ref_id)
        if ref_channel is None:
            print(f"[MonthlyCategory] 基準チャンネル『{REFERENCE_CHANNEL_KEY}』が見つかりません。位置調整をスキップします。")
            return

        # セッション１がカテゴリ配下にあるなら、そのカテゴリの位置に合わせる（＝そのカテゴリの真上に来る）
        # カテゴリ未所属（直下）なら、チャンネル自体の位置に合わせる
        target_position = ref_channel.category.position if ref_channel.category else ref_channel.position

        try:
            await category.edit(position=target_position)
        except discord.HTTPException as e:
            print(f"[MonthlyCategory] カテゴリの位置調整に失敗しました: {e}")

    # ---------------- カテゴリ作成本体 ----------------
    async def create_monthly_category(self, guild: discord.Guild, target_date: datetime.date):
        """対象月のカテゴリが無ければ作成する。
        戻り値: (category, created_now: bool)
        既に同名カテゴリがあれば作成せずそれを返す（重複防止）。
        """
        category_name = get_category_name(target_date)

        existing = discord.utils.get(guild.categories, name=category_name)
        if existing:
            return existing, False

        category = await guild.create_category(category_name)
        await self.position_above_reference(guild, category)
        print(f"[MonthlyCategory] カテゴリ『{category_name}』を作成しました。")
        return category, True

    def _month_key(self, target_date: datetime.date) -> str:
        return f"{target_date.year}-{target_date.month:02d}"

    # ---------------- 自動実行（毎日 0:05 JSTにチェック、MONTHS_AHEADヶ月先を作成） ----------------
    @tasks.loop(time=datetime.time(hour=0, minute=5, tzinfo=JST))
    async def monthly_category_task(self):
        now = datetime.datetime.now(JST)

        if now.day != 1:
            return  # 月初（1日）以外は何もしない

        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            print("[MonthlyCategory] GUILD_IDのサーバーが見つかりません。")
            return

        target_date = add_months(now.date(), MONTHS_AHEAD)

        data = self.load_data()
        month_key = self._month_key(target_date)
        if data.get("last_created") == month_key:
            return  # 既にこの先行月は作成記録あり

        category, created = await self.create_monthly_category(guild, target_date)
        data["last_created"] = month_key
        self.save_data(data)

        if created:
            print(f"[MonthlyCategory] 自動作成完了（{MONTHS_AHEAD}ヶ月先）: {category.name}")

    @monthly_category_task.before_loop
    async def before_monthly_category_task(self):
        await self.bot.wait_until_ready()

        # 再起動でスケジュールを取りこぼしていた場合に備え、
        # 起動時に「MONTHS_AHEADヶ月先のカテゴリが存在するか」を一度だけ確認しておく。
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
        手動で月別カテゴリを作成するコマンド（管理者のみ）。
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

    # ---------------- 卓ログ送信 ----------------
    async def send_session_log(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        session_dt: datetime.datetime,
        mentions: list[str],
    ):
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        if log_channel is None:
            print(f"[MonthlyCategory] ログチャンネル（ID: {LOG_CHANNEL_ID}）が見つかりません。")
            return
        members_str = " ".join(mentions) if mentions else "（なし）"
        embed = discord.Embed(
            title="📋 卓ログ",
            color=discord.Color.blue(),
        )
        embed.add_field(name="📅 開催日時", value=session_dt.strftime("%Y年%m月%d日 %H:%M"), inline=False)
        embed.add_field(name="📺 チャンネル", value=channel.mention, inline=False)
        embed.add_field(name="👥 参加者", value=members_str, inline=False)
        await log_channel.send(embed=embed)

    # ---------------- サイレントリマインド送信 ----------------
    async def _reminder_task(
        self,
        channel: discord.TextChannel,
        session_dt: datetime.datetime,
        mentions: list[str],
        label: str,
        wait_seconds: float,
    ):
        await asyncio.sleep(wait_seconds)
        mention_str = " ".join(mentions)
        try:
            await channel.send(
                f"🔔 {mention_str}\n"
                f"📅 {label}（{session_dt.strftime('%m月%d日 %H:%M')}）に卓があります！",
                suppress_notifications=True,
            )
        except Exception as e:
            print(f"[MonthlyCategory] リマインド送信失敗（{label}）: {e}")

    def _schedule_reminder(self, channel, session_dt, mentions, remind_dt, label, now):
        """リマインドをスケジュールし、登録できた場合は remind_dt を返す。過去なら None を返す。"""
        wait_seconds = (remind_dt - now).total_seconds()
        if wait_seconds <= 0:
            return None
        task = asyncio.create_task(
            self._reminder_task(channel, session_dt, mentions, label, wait_seconds)
        )
        self._pending_reminders.append(task)
        task.add_done_callback(
            lambda t: self._pending_reminders.remove(t) if t in self._pending_reminders else None
        )
        return remind_dt

    # ---------------- 手動コマンド：シンプル移動（!m2m 月/日） ----------------
    @commands.command(name="m2m")
    @is_gm_or_admin()
    async def m2m(self, ctx, date_str: str):
        """
        コマンドを打ったチャンネルを指定した月のカテゴリへ移動する（GMロール or 管理者のみ）。
        時刻・メンション不要のシンプル版。ログ・通知なし。
        使い方: !m2m 7/15
        """
        if not is_allowed_category(ctx.channel.category):
            await ctx.send("このチャンネルではこのコマンドは使えません。")
            return

        parts = date_str.split("/")
        if len(parts) != 2:
            await ctx.send("入力形式が正しくありません。例: `!m2m 7/15`")
            return

        try:
            month, day = int(parts[0]), int(parts[1])
        except ValueError:
            await ctx.send("入力形式が正しくありません。例: `!m2m 7/15`")
            return

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
                f"先に `!createmonthlycategory {year} {month}` で作成してください。"
            )
            return

        try:
            await ctx.channel.edit(category=category, sync_permissions=False)
        except discord.HTTPException as e:
            print(f"[ERROR] m2m: {e}")
            await ctx.send("チャンネルの移動に失敗しました。Botの権限を確認してください。")
            return

        self.save_channel_date(ctx.channel.id, target_date)
        await self.sort_category_by_date(category)
        await ctx.send(f"✅ このチャンネルを『{category_name}』に移動し、開催日順に並び替えました。")

    @m2m.error
    async def m2m_error(self, ctx, error):
        if isinstance(error, NotGMOrAdmin):
            await ctx.send("このコマンドはGMロールまたは管理者のみ使用できます。")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("月/日を指定してください。例: `!m2m 7/15`")
        else:
            print(f"[ERROR] m2m: {error}")
            await ctx.send("エラーが発生しました。")

    # ---------------- 手動コマンド：拡張移動（!m2m2 月/日/時分 @mentions） ----------------
    @commands.command(name="m2m2")
    @is_gm_or_admin()
    async def m2m2(self, ctx, date_str: str, *members: discord.Member):
        """
        チャンネル移動 + ログ記録 + 1日前・1時間前にサイレント通知（GMロール or 管理者のみ）。
        使い方:
          !m2m2 7/15/1800              → 7月15日18時のカテゴリへ移動
          !m2m2 7/15/1800 @user1 @user2 → 上記 + ログ記録 & 1日前・1時間前にサイレント通知
        """
        if not is_allowed_category(ctx.channel.category):
            await ctx.send("このチャンネルではこのコマンドは使えません。")
            return

        # ── 日付・時刻パース ──
        parts = date_str.split("/")
        if len(parts) != 3:
            await ctx.send("入力形式が正しくありません。例: `!m2m2 7/15/1800`")
            return

        try:
            month = int(parts[0])
            day   = int(parts[1])
            hour, minute = parse_time(parts[2])
        except ValueError as e:
            await ctx.send(f"入力形式が正しくありません: {e}\n例: `!m2m2 7/15/1800`")
            return

        now = datetime.datetime.now(JST)
        year = now.year if month >= now.month else now.year + 1

        try:
            session_dt = datetime.datetime(year, month, day, hour, minute, tzinfo=JST)
        except ValueError:
            await ctx.send("存在しない日付・時刻です。確認してください。")
            return

        # ── カテゴリ移動 ──
        category_name = get_category_name(session_dt.date())
        category = discord.utils.get(ctx.guild.categories, name=category_name)

        if category is None:
            await ctx.send(
                f"カテゴリ『{category_name}』が見つかりません。"
                f"先に `!createmonthlycategory {year} {month}` で作成してください。"
            )
            return

        try:
            await ctx.channel.edit(category=category, sync_permissions=False)
        except discord.HTTPException as e:
            print(f"[ERROR] m2m2: {e}")
            await ctx.send("チャンネルの移動に失敗しました。Botの権限を確認してください。")
            return

        self.save_channel_date(ctx.channel.id, session_dt.date())
        await self.sort_category_by_date(category)

        await ctx.send(
            f"✅ このチャンネルを『{category_name}』に移動し、開催日順に並び替えました。\n"
            f"📅 開催日時: {session_dt.strftime('%Y年%m月%d日 %H:%M')}"
        )

        if not members:
            return

        mentions = [m.mention for m in members]

        # ログ送信
        await self.send_session_log(ctx.guild, ctx.channel, session_dt, mentions)

        # ── 1日前・1時間前のサイレントリマインドをスケジュール ──
        remind_1day  = session_dt - datetime.timedelta(days=1)
        remind_1hour = session_dt - datetime.timedelta(hours=1)

        scheduled = []
        if self._schedule_reminder(ctx.channel, session_dt, mentions, remind_1day, "1日後", now):
            scheduled.append(f"📬 1日前: {remind_1day.strftime('%m月%d日 %H:%M')}")
        if self._schedule_reminder(ctx.channel, session_dt, mentions, remind_1hour, "1時間後", now):
            scheduled.append(f"📬 1時間前: {remind_1hour.strftime('%m月%d日 %H:%M')}")

        if scheduled:
            await ctx.send("⏰ サイレント通知を登録しました。\n" + "\n".join(scheduled))
        else:
            await ctx.send("⚠️ 通知タイミングがすでに過ぎているため登録しませんでした。")

    @m2m2.error
    async def m2m2_error(self, ctx, error):
        if isinstance(error, NotGMOrAdmin):
            await ctx.send("このコマンドはGMロールまたは管理者のみ使用できます。")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("日時を指定してください。例: `!m2m2 7/15/1800`")
        else:
            print(f"[ERROR] m2m2: {error}")
            await ctx.send("エラーが発生しました。")


async def setup(bot):
    await bot.add_cog(MonthlyCategory(bot))
