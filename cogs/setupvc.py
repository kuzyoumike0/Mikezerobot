import discord
from discord.ext import commands
from discord.ui import View, Button
from datetime import datetime, timedelta, timezone
from config import VC_CHANNEL_ID, VC_CATEGORY_ID, SPECIAL_ROLE_ID, ALLOWED_TEXT_CHANNEL_ID


class DeleteChannelButton(discord.ui.View):

    def __init__(self, channel: discord.TextChannel, author: discord.Member):
        super().__init__(timeout=None)
        self.channel = channel
        self.author = author

    @discord.ui.button(label="このチャンネルを削除", style=discord.ButtonStyle.danger)
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.author or interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("チャンネルを削除します...", ephemeral=True)
            await self.channel.delete()
        else:
            await interaction.response.send_message(
                "削除できるのは、コマンド実行者または管理者のみです。", ephemeral=True)


class VCChannelView(discord.ui.View):

    def __init__(self, bot: commands.Bot, author: discord.Member):
        super().__init__(timeout=None)
        self.bot = bot
        self.author = author

    @discord.ui.button(label="VC参加者共有チャンネル作成", style=discord.ButtonStyle.primary)
    async def create_shared(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        vc = guild.get_channel(VC_CHANNEL_ID)
        members = [m for m in vc.members if not m.bot]

        if not members:
            await interaction.response.send_message("VCに誰もいません。", ephemeral=True)
            return

        jst = timezone(timedelta(hours=9))
        now = datetime.now(jst)
        now_str = now.strftime("%Y%m%d-%H%M-JST")
        channel_name = f"vc-{now_str}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }
        for member in members:
            overwrites[member] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True)

        role = guild.get_role(SPECIAL_ROLE_ID)
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)

        category = discord.utils.get(guild.categories, id=VC_CATEGORY_ID)
        channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=category)

        view = DeleteChannelButton(channel=channel, author=self.author)
        await channel.send("このチャンネルを削除するには以下のボタンを押してください。", view=view)
        await interaction.response.send_message(f"{channel.mention} を作成しました。", ephemeral=False)

    @discord.ui.button(label="VC参加者個別チャンネル作成", style=discord.ButtonStyle.secondary)
    async def create_individual(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        vc = guild.get_channel(VC_CHANNEL_ID)
        members = [m for m in vc.members if not m.bot]

        if not members:
            await interaction.response.send_message("VCに誰もいません。", ephemeral=True)
            return

        jst = timezone(timedelta(hours=9))
        now = datetime.now(jst)
        date_str = now.strftime("%Y%m%d")

        category = discord.utils.get(guild.categories, id=VC_CATEGORY_ID)
        created_channels = []

        for member in members:
            nickname = member.nick if member.nick else member.name
            channel_name = f"{nickname}-{date_str}".replace(" ", "-").lower()
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }

            role = guild.get_role(SPECIAL_ROLE_ID)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)

            channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=category)
            view = DeleteChannelButton(channel=channel, author=self.author)
            await channel.send(f"{member.mention} の個別チャンネルです。削除ボタンはこちら👇", view=view)
            created_channels.append(channel.mention)

        await interaction.response.send_message("個別チャンネルを作成しました。\n" + "\n".join(created_channels), ephemeral=False)


class SetupVC(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def setupvc(self, ctx):
        if ctx.channel.id != ALLOWED_TEXT_CHANNEL_ID:
            await ctx.send("このチャンネルでは `!setupvc` コマンドは使用できません。", delete_after=10)
            return
        await ctx.send("VC参加者用のチャンネルを作成できます：", view=VCChannelView(bot=self.bot, author=ctx.author))


async def setup(bot):
    await bot.add_cog(SetupVC(bot))
