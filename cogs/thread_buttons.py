import discord
from discord.ext import commands
from discord.ui import View, Button
from config import PRIVATE_CATEGORY_ID  # ← config からカテゴリIDを読み込み

class PrivateChannelButtons(View):
    def __init__(self, bot, thread, author, thread_name):
        super().__init__(timeout=None)
        self.bot = bot
        self.thread = thread
        self.author = author
        self.thread_name = thread_name
        self.channel_id = None

    @discord.ui.button(label="プライベートチャンネル作成", style=discord.ButtonStyle.green)
    async def create_private_channel(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ この操作はスレッド作成者のみが実行できます。", ephemeral=True)
            return

        if self.channel_id is not None:
            await interaction.response.send_message("⚠️ すでにプライベートチャンネルは作成されています。", ephemeral=True)
            return

        guild = interaction.guild
        category = guild.get_channel(PRIVATE_CATEGORY_ID)
        if category is None or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ 指定されたカテゴリが存在しません。管理者に連絡してください。", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            self.author: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=self.thread_name,
            category=category,
            overwrites=overwrites,
            reason="プライベートチャンネル作成"
        )

        self.channel_id = channel.id

        await interaction.response.send_message(
            f"✅ プライベートチャンネル `{channel.name}` を `{category.name}` に作成しました。\n"
            f"{self.author.mention} は自動的に参加済みです。",
            ephemeral=True
        )

    @discord.ui.button(label="プライベートチャンネルに参加", style=discord.ButtonStyle.blurple)
    async def join_private_channel(self, interaction: discord.Interaction, button: Button):
        if self.channel_id is None:
            await interaction.response.send_message("❌ まだプライベートチャンネルが作成されていません。", ephemeral=True)
            return

        channel = self.bot.get_channel(self.channel_id)
        if channel is None:
            await interaction.response.send_message("❌ チャンネルが見つかりません。", ephemeral=True)
            return

        await channel.set_permissions(interaction.user, view_channel=True, send_messages=True)
        await interaction.response.send_message(f"✅ {channel.mention} に参加させました。", ephemeral=True)


class ThreadButtonCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="start_thread")
    async def start_thread(self, ctx: commands.Context, *, thread_name: str = None):
        if not thread_name:
            await ctx.send("⚠️ スレッド名を指定してください。\n使用例：`!start_thread 作戦会議`")
            return

        thread = await ctx.channel.create_thread(
            name=thread_name,
            type=discord.ChannelType.public_thread,
            auto_archive_duration=60
        )

        view = PrivateChannelButtons(self.bot, thread, ctx.author, thread_name)
        await thread.send(
            f"{ctx.author.mention} スレッドが作成されました。\nボタンを使ってプライベートチャンネルを操作できます。",
            view=view
        )

async def setup(bot):
    await bot.add_cog(ThreadButtonCog(bot))
