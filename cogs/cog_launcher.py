import discord
from discord.ext import commands

GM_ROLE_NAME = "GM"


class NotGMOrAdmin(commands.CheckFailure):
    pass


def is_gm_or_admin():
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.author.guild_permissions.administrator:
            return True
        if discord.utils.get(ctx.author.roles, name=GM_ROLE_NAME):
            return True
        raise NotGMOrAdmin("GMロールまたは管理者のみ使用できます。")
    return commands.check(predicate)


class CogLauncherView(discord.ui.View):
    """1ボタン＝1cogを起動するための永続View。

    ボタンを増やしたいときは、下にある
    「🔽 テンプレート」〜「🔼 テンプレートここまで」のブロックを
    まるごとコピーして増やしてください。
    """

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    # ==========================================================
    # 🔽 テンプレート：ここから1ブロック＝1つのcog起動ボタン
    #
    # 複製する手順:
    #   1. このブロック全体（@discord.ui.button 〜 メソッド終わりまで）をコピー
    #   2. label と custom_id を新しい名前に変更（custom_id は必ずボタンごとに一意）
    #   3. メソッド名 (launch_sample_cog) を分かりやすい名前に変更
    #   4. get_cog("SampleCog") の文字列を、起動したいCogのクラス名に変更
    #   5. 「ここに新規cogsの起動コードを書く」の中身を実装
    # ==========================================================
    @discord.ui.button(
        label="サンプルCog起動",
        style=discord.ButtonStyle.primary,
        custom_id="cog_launcher:sample_cog",
    )
    async def launch_sample_cog(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_cog = self.bot.get_cog("SampleCog")  # ← 起動したいCogのクラス名に変更
        if target_cog is None:
            await interaction.response.send_message(
                "❌ SampleCog が見つかりません。cogsフォルダに追加されているか確認してください。",
                ephemeral=True,
            )
            return

        # ▼▼▼ ここに新規cogsの起動コードを書く ▼▼▼

        # 例1: 起動したいcog側に専用メソッド（例: start）を用意して呼び出す
        # await target_cog.start(interaction)

        # 例2: cogが持っている!コマンドをそのまま実行する
        # ctx = await self.bot.get_context(interaction.message)
        # await target_cog.some_command(ctx)

        # ▲▲▲ ここまで ▲▲▲

        await interaction.response.send_message("✅ SampleCog を起動しました！", ephemeral=True)
    # ==========================================================
    # 🔼 テンプレートここまで
    # ==========================================================

    # ==========================================================
    # チャンネル削除ボタン（!delete は直接打っても実行不可。このボタンからのみ !delete を起動する）
    # ==========================================================
    @discord.ui.button(
        label="チャンネル削除",
        style=discord.ButtonStyle.danger,
        custom_id="cog_launcher:delete_channel",
    )
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_manage_channels = interaction.user.guild_permissions.manage_channels
        has_gm_role = discord.utils.get(interaction.user.roles, name=GM_ROLE_NAME) is not None

        if not (has_manage_channels or has_gm_role):
            await interaction.response.send_message(
                "❌ このボタンは「チャンネルの管理」権限を持つ人、またはGMロールの人のみ使用できます。",
                ephemeral=True,
            )
            return

        delete_command = self.bot.get_command("delete")
        if delete_command is None:
            await interaction.response.send_message(
                "❌ delete コマンドが読み込まれていません（cogs/delete_channel.py を確認してください）。",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        # !delete コマンドをボタン経由で起動する（ctx.author を押した人に差し替える）
        ctx = await self.bot.get_context(interaction.message)
        ctx.author = interaction.user
        ctx.from_launcher = True
        await ctx.invoke(delete_command)
    # ==========================================================


class CogLauncher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Bot再起動後もボタンを押せるように、永続Viewとして登録しておく
        self.bot.add_view(CogLauncherView(bot))

    @commands.command(name="call")
    @is_gm_or_admin()
    async def call(self, ctx: commands.Context):
        """cog起動ボタンのパネルを設置する（管理者 or GMロールのみ）"""
        embed = discord.Embed(
            title="🚀 機能起動パネル",
            description="ボタンを押すと、対応するcogの機能が起動します。",
            color=discord.Color.gold(),
        )
        await ctx.send(embed=embed, view=CogLauncherView(self.bot))

    @call.error
    async def call_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, NotGMOrAdmin):
            await ctx.send("❌ このコマンドは管理者またはGMロールのみ使用できます。")


async def setup(bot: commands.Bot):
    await bot.add_cog(CogLauncher(bot))
