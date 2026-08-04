import discord
from discord.ext import commands

from config import VC_CHANNEL_IDS


class VCDebug(commands.Cog):
    """!setupvc がVCを見つけられない原因を切り分けるための診断コマンド。"""

    def __init__(self, bot):
        self.bot = bot

    async def diagnose(self, guild: discord.Guild, name: str, vc_id: int) -> str:
        lines = [f"**{name}** (`{vc_id}`)"]

        channel = guild.get_channel(vc_id)
        if channel is None:
            # キャッシュにない場合、APIに直接問い合わせて理由を切り分ける
            lines.append("  ❌ get_channel: None（キャッシュに存在しない）")
            try:
                fetched = await self.bot.fetch_channel(vc_id)
                lines.append(f"  ⚠️ APIには存在: {type(fetched).__name__} / 名前『{fetched.name}』")
                lines.append("  → Botのキャッシュに乗っていません。Botの再起動で直る可能性があります。")
            except discord.NotFound:
                lines.append("  → このIDのチャンネルは**存在しません**（削除済み）。config.pyのIDが古いです。")
            except discord.Forbidden:
                lines.append("  → Botにこのチャンネルの**閲覧権限がありません**。チャンネルの権限設定を確認してください。")
            except discord.HTTPException as e:
                lines.append(f"  → 取得失敗: {type(e).__name__} {e}")
            return "\n".join(lines)

        lines.append(f"  ✅ 発見: 『{channel.name}』 種別: `{type(channel).__name__}`")

        if not isinstance(channel, discord.VoiceChannel):
            lines.append("  ❌ ボイスチャンネルではありません（ステージチャンネル等）。!setupvc は対応していません。")
            return "\n".join(lines)

        category = channel.category
        if category is None:
            lines.append("  ❌ カテゴリに属していません（作成先が決まらないため作成できません）。")
        else:
            can_manage = category.permissions_for(guild.me).manage_channels
            lines.append(
                f"  作成先カテゴリ: 『{category.name}』 "
                f"作成権限={'✅' if can_manage else '❌ 「チャンネルの管理」がありません'} "
                f"({len(category.channels)}/50)"
            )

        perms = channel.permissions_for(guild.me)
        lines.append(
            f"  Bot権限: 閲覧={'✅' if perms.view_channel else '❌'} "
            f"接続={'✅' if perms.connect else '❌'}"
        )

        members = [m for m in channel.members if not m.bot]
        if members:
            lines.append(f"  👥 在室者({len(members)}人): {', '.join(m.display_name for m in members)}")
        else:
            lines.append("  ⚠️ **在室者0人** → この状態で押すと「VCに参加者がいません」で何も作成されません。")

        return "\n".join(lines)

    @commands.command(name="vccheck")
    @commands.has_permissions(manage_channels=True)
    async def vccheck(self, ctx):
        """VC_CHANNEL_IDS の各VCの状態を比較表示する（管理者のみ）"""
        guild = ctx.guild
        blocks = []

        for name, vc_id in VC_CHANNEL_IDS.items():
            blocks.append(await self.diagnose(guild, name, vc_id))

        await ctx.send("🔍 **VC設定診断**\n\n" + "\n\n".join(blocks))

    @vccheck.error
    async def vccheck_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("このコマンドは「チャンネルの管理」権限を持つ人のみ使用できます。")


async def setup(bot):
    await bot.add_cog(VCDebug(bot))
