import discord
from discord import app_commands
from discord.ext import commands
from cogs.delete_channel import get_allowed_category_ids


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

        lines = []
        for category_id in get_allowed_category_ids():
            category = interaction.guild.get_channel(category_id)
            name = category.name if category else "（見つかりません）"
            lines.append(f"- {name} (`{category_id}`)")

        embed = discord.Embed(
            title="🗂️ 削除許可カテゴリ一覧",
            description="\n".join(lines) if lines else "登録されているカテゴリはありません。",
            color=discord.Color.blurple(),
        )
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


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminLauncher(bot))
