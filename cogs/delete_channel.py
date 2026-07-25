import discord
from discord.ext import commands
from datetime import datetime, timezone
from config import DELETE_ALLOWED_CATEGORY_IDS, AUDIT_LOG_CHANNEL_ID


def launcher_only():
    """launcherのボタン経由（ctx.from_launcher=True）以外での実行を弾くチェック。"""
    async def predicate(ctx: commands.Context) -> bool:
        return getattr(ctx, "from_launcher", False)
    return commands.check(predicate)


async def reply(ctx: commands.Context, content: str):
    """launcher経由なら実行者本人にしか見えないephemeralで返す。"""
    interaction = getattr(ctx, "interaction", None)
    if interaction is not None:
        await interaction.followup.send(content, ephemeral=True)
    else:
        await ctx.send(content)


class DeleteChannel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ctx.invoke() 経由（cog_launcher.pyのボタン）でのみ実行される想定のコマンド。
    # 直接 !delete と打っても launcher_only のチェックで弾かれる。
    @commands.command(name="delete", hidden=True)
    @launcher_only()
    async def delete(self, ctx: commands.Context):
        channel = ctx.channel

        if not isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
            await reply(ctx, "❌ このチャンネルは削除できません。")
            return

        if channel.category_id not in DELETE_ALLOWED_CATEGORY_IDS:
            await reply(ctx, "❌ このチャンネルは削除対象のカテゴリに含まれていないため削除できません。")
            return

        await reply(ctx, f"🗑️ 「{channel.name}」を削除します...")
        await self.send_audit_log(ctx.guild, ctx.author, channel)
        await channel.delete(reason=f"{ctx.author} がチャンネル削除ボタン経由で !delete を実行")

    async def send_audit_log(self, guild: discord.Guild, author: discord.Member, channel: discord.abc.GuildChannel):
        log_channel = guild.get_channel(AUDIT_LOG_CHANNEL_ID)
        if log_channel is None:
            return

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        embed = discord.Embed(
            title="🗑️ チャンネル削除ログ",
            color=discord.Color.red(),
        )
        embed.add_field(name="実行者", value=f"{author.mention} ({author})", inline=False)
        embed.add_field(name="削除されたチャンネル", value=f"#{channel.name} (ID: {channel.id})", inline=False)
        embed.add_field(name="日時", value=now, inline=False)

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(DeleteChannel(bot))
