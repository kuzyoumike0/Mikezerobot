import discord
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="helpme")
    async def helpme(self, ctx):
        embed = discord.Embed(
            title="📚 Botの機能一覧",
            description="使用できるコマンドと説明：",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🔊 !joinvc",
            value="Botをボイスチャットに接続します。入退室時に時間帯ごとの効果音を流します。",
            inline=False
        )
        embed.add_field(
            name="🗳️ !startvote 質問 | 選択肢1 | 選択肢2 | ...",
            value="匿名投票を開始し、終了後に結果を表示（DM対応）",
            inline=False
        )
        embed.add_field(
            name="👥 !creategroup <チャンネル名>",
            value="参加ボタンを表示し、押したユーザーでプライベートチャンネルを作成",
            inline=False
        )
        embed.add_field(
            name="🔑 !joinprivate <ユーザー名>",
            value="指定したユーザーをこのチャンネルに追加",
            inline=False
        )
        embed.add_field(
            name="🎛️ !setupvc",
            value="VC参加者用の共有・個別チャンネル作成ボタンを表示",
            inline=False
        )
        embed.add_field(
            name="⏱️ !vctimer <分>",
            value="このチャンネルにタイマーを設定（5分前・1分前・終了で通知）",
            inline=False
        )
        embed.add_field(
            name="📩 !resultvote <メッセージID>",
            value="匿名投票の集計結果を表示（startvoteで使ったID）",
            inline=False
        )
        embed.add_field(
            name="📥 !exportlog <チャンネル> [txt|html]",
            value="指定チャンネルのログをtxtまたはhtml形式でDM送信します",
            inline=False
        )
        embed.add_field(
            name="🔄 !restart",
            value="Botを再起動します（管理者用）",
            inline=False
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))
