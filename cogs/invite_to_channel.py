import discord
from discord.ext import commands


def launcher_only():
    """launcherのボタン経由（ctx.from_launcher=True）以外での実行を弾くチェック。"""
    async def predicate(ctx: commands.Context) -> bool:
        return getattr(ctx, "from_launcher", False)
    return commands.check(predicate)


async def reply(ctx: commands.Context, content: str, **kwargs):
    """launcher経由なら実行者本人にしか見えないephemeralで返す。"""
    interaction = getattr(ctx, "interaction", None)
    if interaction is not None:
        await interaction.followup.send(content, ephemeral=True, **kwargs)
    else:
        await ctx.send(content, **kwargs)


class InviteUserSelect(discord.ui.UserSelect):
    def __init__(self, channel: discord.abc.GuildChannel):
        super().__init__(placeholder="招待するユーザーを選択", min_values=1, max_values=5)
        self.channel = channel

    async def callback(self, interaction: discord.Interaction):
        invited = []
        for member in self.values:
            await self.channel.set_permissions(member, view_channel=True, send_messages=True)
            invited.append(member.mention)

        await interaction.response.send_message(f"✅ 招待しました: {' '.join(invited)}", ephemeral=True)


class InviteView(discord.ui.View):
    def __init__(self, channel: discord.abc.GuildChannel):
        super().__init__(timeout=60)
        self.add_item(InviteUserSelect(channel))


class InviteToChannel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ctx.invoke() 経由（cog_launcher.pyのボタン）でのみ実行される想定のコマンド。
    # 直接 !in と打っても launcher_only のチェックで弾かれる。
    @commands.command(name="in", hidden=True)
    @launcher_only()
    async def invite(self, ctx: commands.Context):
        channel = ctx.channel

        if not isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
            await reply(ctx, "❌ このチャンネルには招待できません。")
            return

        await reply(ctx, "招待するユーザーを選んでください。", view=InviteView(channel))


async def setup(bot: commands.Bot):
    await bot.add_cog(InviteToChannel(bot))
