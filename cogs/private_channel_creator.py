import discord
from discord.ext import commands
from discord.ui import View, Button
from config import CATEGORY_ID

class PrivateChannelView(View):
    def __init__(self, bot, initiator: discord.Member, channel_name: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.initiator = initiator
        self.channel_name = channel_name
        self.participants = set()
        self.channel = None

    @discord.ui.button(label="参加する", style=discord.ButtonStyle.success, custom_id="join_button")
    async def join_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id in self.participants:
            await interaction.response.send_message("すでに参加済みです。", ephemeral=True)
            return

        self.participants.add(interaction.user.id)

        if self.channel:
            await self.channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            await interaction.response.send_message(f"{self.channel.mention} に参加しました！", ephemeral=True)

    @discord.ui.button(label="チャンネルを削除", style=discord.ButtonStyle.danger, custom_id="delete_button")
    async def delete_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.initiator and not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("このチャンネルを削除できるのは作成者または管理者のみです。", ephemeral=True)
            return

        if self.channel:
            await self.channel.delete()
            await interaction.response.send_message("チャンネルを削除しました。", ephemeral=True)


class PrivateChannelCreator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def create_private(self, ctx, *, channel_name: str):
        """参加者限定のプライベートチャンネルを作成"""
        guild = ctx.guild
        category = guild.get_channel(CATEGORY_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

        view = PrivateChannelView(self.bot, ctx.author, channel_name)
        view.participants.add(ctx.author.id)
        view.channel = channel

        await ctx.send(
            f"✅ プライベートチャンネル **{channel_name}** を作成しました！参加者は下のボタンを押してください。
            日程調整終了後、【!m2m 月/日】でカテゴリ移動をお願いします。",
            view=view
        )

        await channel.send(f"🔒 このチャンネルは **{ctx.author.display_name}** により作成されました。")
        await channel.send("チャンネルを削除したい場合は以下のボタンを押してください。", view=view)


async def setup(bot):
    await bot.add_cog(PrivateChannelCreator(bot))
