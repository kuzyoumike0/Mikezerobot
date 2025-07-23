import discord
from discord.ext import commands
from discord.ui import View, Button
from datetime import timezone, timedelta
from config import VC_CHANNEL_IDS, SECRET_CATEGORY_ID, ALLOWED_TEXT_CHANNEL_ID

# 削除ボタン付きViewクラス
class DeleteChannelButton(discord.ui.View):
    def __init__(self, channel: discord.TextChannel, author: discord.Member):
        super().__init__(timeout=None)
        self.channel = channel
        self.author = author

    @discord.ui.button(label="このチャンネルを削除", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.author or interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("チャンネルを削除します...", ephemeral=True)
            await self.channel.delete()
        else:
            await interaction.response.send_message("削除権限がありません。", ephemeral=True)

class SetupSecret(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setupsecret")
    async def setupsecret(self, ctx, channel_name: str, vc_name: str):
        # コマンド使用チャンネル制限
        if ctx.channel.id != ALLOWED_TEXT_CHANNEL_ID:
            await ctx.send("このチャンネルでは使用できません。", delete_after=10)
            return

        guild = ctx.guild

        # VC名が辞書に存在するか確認
        if vc_name not in VC_CHANNEL_IDS:
            await ctx.send(f"VC名「{vc_name}」は無効です。", delete_after=10)
            return

        vc_channel = guild.get_channel(VC_CHANNEL_IDS[vc_name])
        if not vc_channel:
            await ctx.send("指定されたVCが見つかりません。", delete_after=10)
            return

        # VCに参加しているメンバー（bot除外）
        members = [m for m in vc_channel.members if not m.bot]
        if not members:
            await ctx.send("VCに参加している人がいません。", delete_after=10)
            return

        # 密談チャンネル用カテゴリを取得
        category = discord.utils.get(guild.categories, id=SECRET_CATEGORY_ID)
        if not category:
            await ctx.send("密談用カテゴリが見つかりません。", delete_after=10)
            return

        # チャンネルのパーミッション設定
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }
        for member in members:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # テキストチャンネル作成
        new_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

        # 削除ボタンを付けてメッセージ送信
        view = DeleteChannelButton(channel=new_channel, author=ctx.author)
        await new_channel.send(f"{ctx.author.mention} が作成した密談チャンネルです。削除ボタンはこちら👇", view=view)

        await ctx.send(f"{new_channel.mention} を作成しました。", delete_after=20)

async def setup(bot):
    await bot.add_cog(SetupSecret(bot))
