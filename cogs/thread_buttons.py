import discord
from discord.ext import commands
from discord.ui import View, Button

class PrivateChannelButtons(View):
    def __init__(self, bot, thread, author):
        super().__init__(timeout=None)
        self.bot = bot
        self.thread = thread
        self.author = author
        self.channel_id = None  # 作成されたチャンネルIDを記録

    @discord.ui.button(label="プライベートチャンネル作成", style=discord.ButtonStyle.green)
    async def create_private_channel(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ この操作はスレッド作成者のみが実行できます。", ephemeral=True)
            return

        if self.channel_id is not None:
            await interaction.response.send_message("⚠️ すでにプライベートチャンネルは作成されています。", ephemeral=True)
            return

        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            self.author: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"private-{self.author.name}",
            overwrites=overwrites,
            reason="プライベートチャンネル作成"
        )

        self.channel_id = channel.id

        await interaction.response.send_message(
            f"✅ プライベートチャンネルを作成しました: {channel.mention}\n"
            f"{self.author.mention} は自動的にチャンネルに参加しています。",
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
        await interaction.response.send_message(f"✅ あなたを {channel.mention} に追加しました。", ephemeral=True)


class ThreadButtonCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="start_thread")
    async def start_thread(self, ctx: commands.Context):
        # スレッド作成
        thread = await ctx.channel.create_thread(
            name=f"{ctx.author.name}のスレッド",
            type=discord.ChannelType.public_thread,
            auto_archive_duration=60
        )

        # ボタン表示
        view = PrivateChannelButtons(self.bot, thread, ctx.author)
        await thread.send(
            f"{ctx.author.mention} スレッドが作成されました。以下のボタンでプライベートチャンネルを作成・参加できます。",
            view=view
        )

async def setup(bot):
    await bot.add_cog(ThreadButtonCog(bot))
