# cogs/setupvc.py
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

    def get_vc_members(self, guild: discord.Guild):
        vc_id = VC_CHANNEL_IDS.get(self.vc_name)
        if not vc_id:
            return None, f"設定エラー: VC_CHANNEL_IDS に『{self.vc_name}』が見つかりません。"
        vc_channel = guild.get_channel(vc_id)
        if vc_channel is None:
            return None, f"VCが見つかりません（ID: {vc_id}）。Botの権限や設定を確認してください。"
        if not isinstance(vc_channel, discord.VoiceChannel):
            return None, f"指定IDはボイスチャンネルではありません（ID: {vc_id}）。"
        members = [m for m in vc_channel.members if not m.bot]
        return members, None

    @discord.ui.button(label="VC参加者共有チャンネル作成", style=discord.ButtonStyle.primary)
    async def create_shared(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True)
            guild = interaction.guild

            members, err = self.get_vc_members(guild)
            if err:
                await interaction.followup.send(f"❌ {err}", ephemeral=True)
                return
            if not members:
                await interaction.followup.send("⚠️ VCに参加者がいません（Botは除外）。", ephemeral=True)
                return

            category = guild.get_channel(VC_CATEGORY_ID)
            if category is None or not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send(f"❌ カテゴリが見つかりません（ID: {VC_CATEGORY_ID}）。", ephemeral=True)
                return

            me = guild.me
            if not category.permissions_for(me).manage_channels:
                await interaction.followup.send("❌ Botに『チャンネルの管理』権限がありません。", ephemeral=True)
                return

            now = datetime.now(timezone(timedelta(hours=9)))
            channel_name = f"{self.vc_name.lower()}-{now.strftime('%Y%m%d-%H%M')}"

            overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
            for m in members:
                overwrites[m] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )

            role = guild.get_role(SPECIAL_ROLE_ID)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=False, read_message_history=True
                )

            channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=category)
            view = DeleteChannelButton(channel=channel, author=self.author)
            await channel.send("このチャンネルを削除するには以下のボタンを押してください。", view=view)
            await interaction.followup.send(f"✅ 共有チャンネルを作成しました：{channel.mention}", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ エラー: {type(e).__name__} {e}", ephemeral=True)
            raise

    @discord.ui.button(label="VC参加者個別チャンネル作成", style=discord.ButtonStyle.secondary)
    async def create_individual(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True)
            guild = interaction.guild

            members, err = self.get_vc_members(guild)
            if err:
                await interaction.followup.send(f"❌ {err}", ephemeral=True)
                return
            if not members:
                await interaction.followup.send("⚠️ VCに参加者がいません（Botは除外）。", ephemeral=True)
                return

            category = guild.get_channel(VC_CATEGORY_ID)
            if category is None or not isinstance(category, discord.CategoryChannel):
                await interaction.followup.send(f"❌ カテゴリが見つかりません（ID: {VC_CATEGORY_ID}）。", ephemeral=True)
                return

            me = guild.me
            if not category.permissions_for(me).manage_channels:
                await interaction.followup.send("❌ Botに『チャンネルの管理』権限がありません。", ephemeral=True)
                return

            author_in_guild = guild.get_member(self.author.id) or self.author
            now = datetime.now(timezone(timedelta(hours=9)))
            date_str = now.strftime("%Y%m%d")

            created_mentions = []
            for m in members:
                nickname = m.nick or m.name
                channel_name = f"{nickname}-{self.vc_name.lower()}-{date_str}".replace(" ", "-").lower()

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    m: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                    author_in_guild: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                }
                role = guild.get_role(SPECIAL_ROLE_ID)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=False, read_message_history=True
                    )

                channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=category)
                view = DeleteChannelButton(channel=channel, author=self.author)
                await channel.send(f"{m.mention} の個別チャンネルです。削除ボタンはこちら👇", view=view)
                created_mentions.append(channel.mention)

            await interaction.followup.send("✅ 個別チャンネルを作成しました：\n" + "\n".join(created_mentions), ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ エラー: {type(e).__name__} {e}", ephemeral=True)
            raise

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

# --------------------------
# async setup エントリポイント
# --------------------------
async def setup(bot: commands.Bot):
    await bot.add_cog(SetupVC(bot))
