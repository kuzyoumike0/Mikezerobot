import discord
from discord.ext import commands
import json
import os
import asyncio

from config import GUILD_ID, SESSION_CATEGORY_IDS

SESSION_BASELINE_PATH = "data/session_baseline.json"

# !reset_session を使えるロール名（これ or 管理者のみ）
GM_ROLE_NAME = "GM"


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


class SessionReset(commands.Cog):
    """セッション1〜4カテゴリ内のチャンネル名を、初期状態（Bot初回起動時点の名前）に戻すコグ。
    !reset_session 数字 で個別にリセットできる。
    """

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        asyncio.create_task(self._init_baselines())

    async def _init_baselines(self):
        await self.bot.wait_until_ready()
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            print("[SessionReset] GUILD_IDのサーバーが見つかりません。")
            return

        # まだ初期状態が保存されていないセッションカテゴリがあれば、
        # 「今の状態」を初期状態として自動保存する（後から追加されたカテゴリにも対応）
        data = self.load_data()
        changed = False
        for number, category_id in SESSION_CATEGORY_IDS.items():
            key = str(number)
            if key in data:
                continue  # 既に保存済みなので上書きしない

            category = guild.get_channel(category_id)
            if category is None:
                print(f"[SessionReset] セッション{number}のカテゴリ（ID: {category_id}）が見つかりません。")
                continue

            data[key] = {str(ch.id): ch.name for ch in category.channels}
            changed = True
            print(f"[SessionReset] セッション{number}の初期状態を保存しました（{len(data[key])}件）。")

        if changed:
            self.save_data(data)

    # ---------------- 永続化 ----------------
    def load_data(self) -> dict:
        if not os.path.exists(SESSION_BASELINE_PATH):
            return {}
        try:
            with open(SESSION_BASELINE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def save_data(self, data: dict):
        os.makedirs(os.path.dirname(SESSION_BASELINE_PATH), exist_ok=True)
        with open(SESSION_BASELINE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # ---------------- 手動コマンド ----------------
    @commands.command(name="reset_session")
    @is_gm_or_admin()
    async def reset_session(self, ctx, number: int):
        """
        指定したセッションカテゴリ（1〜4）内のチャンネル名を初期状態に戻す（GMロール or 管理者のみ）。
        使い方: !reset_session 1
        """
        if number not in SESSION_CATEGORY_IDS:
            await ctx.send("セッション番号は1〜4で指定してください。例: `!reset_session 1`")
            return

        category_id = SESSION_CATEGORY_IDS[number]
        category = ctx.guild.get_channel(category_id)
        if category is None:
            await ctx.send(f"セッション{number}のカテゴリが見つかりません。")
            return

        data = self.load_data()
        baseline = data.get(str(number))
        if not baseline:
            await ctx.send(
                f"セッション{number}の初期状態がまだ保存されていません。"
                "Botを一度再起動してから改めて実行してください。"
            )
            return

        restored = 0
        skipped = 0
        for ch in category.channels:
            original_name = baseline.get(str(ch.id))
            if original_name is None:
                skipped += 1
                continue
            if ch.name != original_name:
                try:
                    await ch.edit(name=original_name)
                    restored += 1
                except discord.HTTPException as e:
                    print(f"[SessionReset] チャンネル名の復元に失敗しました（{ch.name}）: {e}")

        msg = f"✅ セッション{number}のチャンネル名を初期状態に戻しました（変更{restored}件）。"
        if skipped:
            msg += f"\n※初期状態に記録のないチャンネルが{skipped}件あったためスキップしました。"
        await ctx.send(msg)

    @reset_session.error
    async def reset_session_error(self, ctx, error):
        if isinstance(error, NotGMOrAdmin):
            await ctx.send("このコマンドはGMロールまたは管理者のみ使用できます。")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("セッション番号を指定してください。例: `!reset_session 1`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("セッション番号は数字で指定してください。例: `!reset_session 1`")
        else:
            print(f"[ERROR] reset_session: {error}")
            await ctx.send("エラーが発生しました。")


async def setup(bot):
    await bot.add_cog(SessionReset(bot))
