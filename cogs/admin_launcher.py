import re

import discord
from discord import app_commands
from discord.ext import commands

from cogs.delete_channel import (
    add_dynamic_allowed_category_id,
    get_allowed_category_ids,
    load_dynamic_allowed_category_ids,
    remove_dynamic_allowed_category_id,
)

# Discord のスノーフレークID（17〜20桁程度）を拾う
ID_PATTERN = re.compile(r"\d{15,25}")


class AdminLauncherView(discord.ui.View):
    """管理者限定の機能パネル用View（/call2）。"""

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    # ==========================================================
    # 削除許可カテゴリ一覧ボタン（管理者限定）
    # ==========================================================
    @discord.ui.button(
        label="削除許可カテゴリ一覧",
        style=discord.ButtonStyle.secondary,
        custom_id="cog_launcher:list_delete_categories",
    )
    async def list_delete_categories(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ このボタンは管理者のみ使用できます。",
                ephemeral=True,
            )
            return

        dynamic_ids = set(load_dynamic_allowed_category_ids())

        lines = []
        for category_id in get_allowed_category_ids():
            category = interaction.guild.get_channel(category_id)
            name = category.name if category else "（見つかりません）"
            mark = "🟢" if category_id in dynamic_ids else "⚪"
            lines.append(f"{mark} {name} (`{category_id}`)")

        embed = discord.Embed(
            title="🗂️ 削除許可カテゴリ一覧",
            description="\n".join(lines) if lines else "登録されているカテゴリはありません。",
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="⚪ config.pyで固定  /  🟢 動的リスト（!DSCdel で解除可）")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    # ==========================================================


class AdminLauncher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Bot再起動後もボタンを押せるように、永続Viewとして登録しておく
        self.bot.add_view(AdminLauncherView(bot))

    @app_commands.command(name="call2", description="管理者限定の機能パネルを表示")
    async def call2(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ このコマンドは管理者のみ使用できます。",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🔧 管理者パネル",
            description="ボタンを押すと起動します。",
            color=discord.Color.dark_gold(),
        )
        await interaction.response.send_message(embed=embed, view=AdminLauncherView(self.bot), ephemeral=True)

    # ==========================================================
    # 削除許可カテゴリの追加／解除（管理者限定）
    # 保存先は delete_channel.py の動的リスト
    # （data/delete_allowed_categories.json）をそのまま利用する。
    # ==========================================================
    @commands.command(name="DSC", aliases=["dsc"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def add_delete_category(self, ctx: commands.Context, *, raw: str = ""):
        """!DSC <カテゴリID> — 削除許可カテゴリを追加する（複数まとめて可）。"""
        category_ids = [int(m) for m in ID_PATTERN.findall(raw)]
        if not category_ids:
            await ctx.reply(
                "使い方: `!DSC <カテゴリID>`\n"
                "スペース区切りで複数まとめて指定できます。",
                mention_author=False,
            )
            return

        already_allowed = set(get_allowed_category_ids())
        added, already, invalid = [], [], []

        for category_id in category_ids:
            channel = ctx.guild.get_channel(category_id)
            if not isinstance(channel, discord.CategoryChannel):
                invalid.append(category_id)
                continue
            if category_id in already_allowed:
                already.append(channel.name)
                continue
            add_dynamic_allowed_category_id(category_id)
            already_allowed.add(category_id)
            added.append(channel.name)

        lines = []
        if added:
            lines.append("✅ 追加しました： " + "、".join(f"**{n}**" for n in added))
        if already:
            lines.append("ℹ️ すでに登録済み： " + "、".join(f"**{n}**" for n in already))
        if invalid:
            lines.append(
                "❌ カテゴリが見つかりません： "
                + "、".join(f"`{i}`" for i in invalid)
                + "\n（カテゴリ以外のチャンネルIDは登録できません）"
            )
        await ctx.reply("\n".join(lines), mention_author=False)

    @commands.command(name="DSCdel", aliases=["dscdel"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def remove_delete_category(self, ctx: commands.Context, *, raw: str = ""):
        """!DSCdel <カテゴリID> — 動的リストから削除許可を解除する。"""
        category_ids = [int(m) for m in ID_PATTERN.findall(raw)]
        if not category_ids:
            await ctx.reply("使い方: `!DSCdel <カテゴリID>`", mention_author=False)
            return

        dynamic_ids = set(load_dynamic_allowed_category_ids())
        removed, missing = [], []

        for category_id in category_ids:
            if category_id not in dynamic_ids:
                missing.append(category_id)
                continue
            remove_dynamic_allowed_category_id(category_id)
            channel = ctx.guild.get_channel(category_id)
            removed.append(channel.name if channel else str(category_id))

        lines = []
        if removed:
            lines.append("🗑️ 解除しました： " + "、".join(f"**{n}**" for n in removed))
        if missing:
            lines.append(
                "ℹ️ 対象外： "
                + "、".join(f"`{i}`" for i in missing)
                + "\n（動的リストに無いIDです。config.pyで固定されている分はここでは外せません）"
            )
        await ctx.reply("\n".join(lines), mention_author=False)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ このコマンドは管理者のみ使用できます。", mention_author=False)
            return
        raise error
    # ==========================================================


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminLauncher(bot))
