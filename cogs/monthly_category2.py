import discord
from discord.ext import commands, tasks
import json
import os
import re
import datetime
from zoneinfo import ZoneInfo

from config import GUILD_ID, VC_CHANNEL_IDS, CATEGORY_ID

# 新カテゴリをこのチャンネルの真上に配置する
REFERENCE_CHANNEL_KEY = "セッション１"

JST = ZoneInfo("Asia/Tokyo")
MONTHLY_CATEGORY_DATA_PATH = "data/monthly_category.json"

# 自動作成は「何ヶ月先」のカテゴリを作るか（例: 3なら7月に11月分を作る）
MONTHS_AHEAD = 3

# !m2m を使えるロール名（これ or 管理者のみ）
GM_ROLE_NAME = "GM"

# このコグが作るカテゴリ名（「2026年7月」など）にマッチする正規表現
MONTHLY_CATEGORY_NAME_PATTERN = re.compile(r"^\d+年\d+月$")

# 既存の「6月開催卓」「7月開催」のような開催月カテゴリにマッチする正規表現
EVENT_MONTH_CATEGORY_NAME_PATTERN = re.compile(r"^\d+月開催卓?$")


def get_category_name(target_date: datetime.date) -> str:
    """対象の年月から「2026年7月」形式のカテゴリ名を作る"""
    return f"{target_date.year}年{target_date.month}月"


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
    """m2mを使ってよいチャンネルかどうか
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

    # ---------------- 指定チャンネルを開催日順の正しい位置へ挿入 ----------------
    async def insert_channel_by_date(self, category: discord.CategoryChannel, target_channel):
        """
        target_channel を、同じ種類（テキスト/ボイス）の既存チャンネルと開催日を
        上から順に比較しながら、自分より遅い日付に達したところで止めて
        その直前に挿入する（挿入ソート方式）。

        例: [A(7/1), B(7/5), C(7/10), D(7/20)] に 7/15 を挿入する場合
          Aと比較 → 7/15の方が遅い → 次へ
          Bと比較 → 7/15の方が遅い → 次へ
          Cと比較 → 7/15の方が遅い → 次へ
          Dと比較 → 7/15の方が早い → Dの直前に挿入
          結果: [A(7/1), B(7/5), C(7/10), 新規(7/15), D(7/20)]

        日付未登録のチャンネルは比較対象に含めない（位置はそのまま動かさない）。
        """
        data = self.load_data()
        channel_dates = data.get("channel_dates", {})

        target_date_str = channel_dates.get(str(target_channel.id))
        if not target_date_str:
            return  # 自分自身に日付がなければ何もしない
        try:
            target_date = datetime.date.fromisoformat(target_date_str)
        except ValueError:
            return

        # 同じ種類のチャンネル一覧（自分以外・日付が登録済みのもののみ）
        if isinstance(target_channel, discord.VoiceChannel):
            siblings = category.voice_channels
        else:
            siblings = category.text_channels

        dated_siblings = []
        for ch in siblings:
            if ch.id == target_channel.id:
                continue
            date_str = channel_dates.get(str(ch.id))
            if not date_str:
                continue
            try:
                d = datetime.date.fromisoformat(date_str)
            except ValueError:
                continue
            dated_siblings.append((ch, d))

        # 既存の並び順（position）を信頼して上から順に比較
        dated_siblings.sort(key=lambda pair: pair[0].position)

        insert_before = None
        for ch, d in dated_siblings:
            if d > target_date:
                insert_before = ch
                break

        try:
            if insert_before is not None:
                await target_channel.move(
                    before=insert_before, category=category, sync_permissions=False
                )
            elif dated_siblings:
                # 自分より遅い日付が無い＝最後尾（日付未登録チャンネルより前）
                last_dated = dated_siblings[-1][0]
                await target_channel.move(
                    after=last_dated, category=category, sync_permissions=False
                )
            else:
                # 日付登録済みの他チャンネルが無ければ先頭でよい
                await target_channel.move(
                    beginning=True, category=category, sync_permissions=False
                )
        except discord.HTTPException as e:
            print(f"[MonthlyCategory] チャンネル挿入に失敗しました（{target_channel.name}）: {e}")

    # ---------------- カテゴリ全体を記録済み日付で完全に再構築 ----------------
    async def full_resort_category(self, category: discord.CategoryChannel):
        """カテゴリ内の全チャンネルを、保存済みの開催日（古い→新しい）順に
        ゼロから並び替える。過去のバージョンで崩れた並びや、
        日付未登録のまま放置されたチャンネルとの不整合をまとめて修正する。

        日付未登録のチャンネルは末尾に残す（元の相対順は維持）。
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
            if len(channels) <= 1:
                return
            ordered = sorted(channels, key=sort_key)
            # 新しい→古いの逆順で1つずつ先頭に積むと、結果的に古い→新しい順になる
            for ch in reversed(ordered):
                try:
                    await ch.move(beginning=True, category=category, sync_permissions=False)
                except discord.HTTPException as e:
                    print(f"[MonthlyCategory] 再ソート中にエラー（{ch.name}）: {e}")

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

    # ---------------- 手動コマンド：シンプル移動（!m2m 月日） ----------------
    @commands.command(name="m2m")
    @is_gm_or_admin()
    async def m2m(self, ctx, date_str: str):
        """
        コマンドを打ったチャンネルを指定した月日のカテゴリへ移動する（GMロール or 管理者のみ）。
        入力は「月日」4桁（例: 0630 → 6月30日）。
        移動と同時に開催日を記録し、その記録を基にカテゴリ内を並び替える。
        使い方: !m2m 0630
        """
        if not is_allowed_category(ctx.channel.category):
            await ctx.send("このチャンネルではこのコマンドは使えません。")
            return

        s = date_str.strip()
        if len(s) != 4 or not s.isdigit():
            await ctx.send("入力形式が正しくありません。例: `!m2m 0630`（6月30日）")
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
        await self.insert_channel_by_date(category, ctx.channel)
        await ctx.send(
            f"✅ このチャンネルを『{category_name}』に移動しました。"
        )

    @m2m.error
    async def m2m_error(self, ctx, error):
        if isinstance(error, NotGMOrAdmin):
            await ctx.send("このコマンドはGMロールまたは管理者のみ使用できます。")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("月日を指定してください。例: `!m2m 0630`")
        else:
            print(f"[ERROR] m2m: {error}")
            await ctx.send("エラーが発生しました。")

    # ---------------- 手動コマンド：移動せず開催日だけ登録 ----------------
    @commands.command(name="SD")
    @is_gm_or_admin()
    async def set_date(self, ctx, date_str: str):
        """
        カテゴリ移動はせず、このチャンネルに開催日だけ登録してカテゴリ内を並び替える
        （GMロール or 管理者のみ）。
        既にカテゴリ内にいるが日付が未登録のチャンネルに後付けで使う。
        入力は「月日」4桁（例: 0630 → 6月30日）。
        使い方: !SD 0630
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
        await self.insert_channel_by_date(ctx.channel.category, ctx.channel)
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
            print(f"[ERROR] set_date: {error}")
            await ctx.send("エラーが発生しました。")

    # ---------------- 手動コマンド：カテゴリ全体を完全に再ソート ----------------
    @commands.command(name="RES")
    @is_gm_or_admin()
    async def resort(self, ctx):
        """
        このチャンネルが所属するカテゴリ全体を、記録済みの開催日に基づいて
        ゼロから並び替える（GMロール or 管理者のみ）。
        過去のバージョンで崩れた並びを一括で直したいときに使う。
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
            print(f"[ERROR] resort: {error}")
            await ctx.send("エラーが発生しました。")


async def setup(bot):
    await bot.add_cog(MonthlyCategory(bot))
