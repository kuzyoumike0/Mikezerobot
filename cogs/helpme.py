import discord
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="helpme")
    async def helpme(self, ctx):
        embed = discord.Embed(
            title="📚 Botの機能一覧",
            description="使用できるコマンドとその説明です。",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🔊 !joinvc",
            value="Botをボイスチャットに接続します。入退室時に時間帯ごとの効果音を流します。",
            inline=False
        )
        embed.add_field(
            name="🗳️ !startvote 質問 | 選択肢1 | 選択肢2 | ...",
            value="匿名投票を開始します。投票はリアクションで行い、終了後に結果をDMで通知します。",
            inline=False
        )
        embed.add_field(
            name="📩 !resultvote <メッセージID>",
            value="匿名投票の集計結果を表示します。startvoteで開始した投票のメッセージIDを指定してください。",
            inline=False
        )
        embed.add_field(
            name="👥 !creategroup <チャンネル名>",
            value="参加ボタンを表示し、参加者のみが閲覧できるプライベートテキストチャンネルを作成します。",
            inline=False
        )
        embed.add_field(
            name="🔑 !joinprivate <ユーザー名>",
            value="現在のプライベートチャンネルに指定したユーザーを追加します。",
            inline=False
        )
        embed.add_field(
            name="🎛️ !setupvc",
            value="対応するVCに接続しているメンバー向けに、共有チャンネル・個別チャンネル作成ボタンを表示します。",
            inline=False
        )
        embed.add_field(
            name="!setupsecret <チャンネル名> <VC名>",
            value="指定したVCに接続中のメンバーのみがアクセス可能な密談用テキストチャンネルを作成します。",
            inline=False
        )
        embed.add_field(
            name="⏱️ !vctimer <分>",
            value="このテキストチャンネルにタイマーを設定します。5分前・1分前・終了時に通知します。",
            inline=False
        )
        embed.add_field(
            name="📥 !exportlog <チャンネル> [txt|html]",
            value="指定チャンネルのログをtxtまたはhtml形式でDM送信します。",
            inline=False
        )
        embed.add_field(
            name="🔄 !restart",
            value="Botを再起動します。（管理者用コマンド）",
            inline=False
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))
