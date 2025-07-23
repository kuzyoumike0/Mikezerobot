import discord
from discord.ext import commands
from discord.ui import View, Button
from datetime import datetime, timedelta, timezone
from config import VC_CHANNEL_IDS, VC_CATEGORY_ID, SPECIAL_ROLE_ID, ALLOWED_TEXT_CHANNEL_ID

# --------------------------
# チャンネル削除ボタンビュー
# --------------------------
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
            await interaction.response.send_message("削除できるのは、コマンド実行者または管理者のみです。", ephemeral=True)

# --------------------------
# VCからのチャンネル作成選択ビュー（共有・個別）
# --------------------------
class VCChannelView(discord.ui.View):
    def __init__(self, bot: commands.Bot, author: discord.Member, vc_name: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.author = author
        self.vc_name = vc_name

    def get_vc_members(self, guild):
        vc_channel = guild.get_channel(VC_CHANNEL_IDS[self.vc_name])
        return [m for m in vc_channel.members if not m.bot] if vc_channel else []

    @discord.ui.button(label="VC参加者共有チャンネル作成", style=discord.ButtonStyle.primary)
    async def create_shared(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        members = self.get_vc_members(guild)

        if not members:
            await interaction.response.send_message("VCに誰もいません。", ephemeral=True)
            return

        now = datetime.now(timezone(timedelta(hours=9)))
        now_str = now.strftime("%Y%m%d-%H%M")
        channel_name = f"{self.vc_name.lower()}-{now_str}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }
        for member in members:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

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
        members = self.get_vc_members(guild)

        if not members:
            await interaction.response.send_message("VCに誰もいません。", ephemeral=True)
            return

        now = datetime.now(timezone(timedelta(hours=9)))
        date_str = now.strftime("%Y%m%d")
        category = discord.utils.get(guild.categories, id=VC_CATEGORY_ID)
        created_channels = []

        for member in members:
            nickname = member.nick if member.nick else member.name
            channel_name = f"{nickname}-{self.vc_name.lower()}-{date_str}".replace(" ", "-").lower()

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                member: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            role = guild.get_role(SPECIAL_ROLE_ID)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)

            channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=category)
            view = DeleteChannelButton(channel=channel, author=self.author)
            await channel.send(f"{member.mention} の個別チャンネルです。削除ボタンはこちら👇", view=view)
            created_channels.append(channel.mention)

        await interaction.response.send_message("個別チャンネルを作成しました：\n" + "\n".join(created_channels), ephemeral=False)

# --------------------------
# VC選択ビュー
# --------------------------
class VCSelectorView(discord.ui.View):
    def __init__(self, bot, author):
        super().__init__(timeout=None)
        self.bot = bot
        self.author = author
        for vc_name in VC_CHANNEL_IDS:
            self.add_item(VCSelectButton(label=vc_name, vc_name=vc_name, bot=bot, author=author))

class VCSelectButton(discord.ui.Button):
    def __init__(self, label, vc_name, bot, author):
        super().__init__(label=label, style=discord.ButtonStyle.success)
        self.vc_name = vc_name
        self.bot = bot
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"「{self.vc_name}」のVCから作成するチャンネルの種類を選んでください：",
            view=VCChannelView(bot=self.bot, author=self.author, vc_name=self.vc_name),
            ephemeral=True
        )

# --------------------------
# Cog定義
# --------------------------
class SetupVC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def setupvc(self, ctx):
        if ctx.channel.id != ALLOWED_TEXT_CHANNEL_ID:
            await ctx.send("このチャンネルでは `!setupvc` コマンドは使用できません。", delete_after=10)
            return
        await ctx.send("どのVCを対象にしますか？", view=VCSelectorView(bot=self.bot, author=ctx.author))

async def setup(bot):
    await bot.add_cog(SetupVC(bot))
