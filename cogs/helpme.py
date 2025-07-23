import discord
from discord.ext import commands

class HelpMe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="helpme")
    async def helpme(self, ctx):
        embed = discord.Embed(
            title="📘 Help - 使用可能なコマンド一覧",
            description="このBotで利用できる主なコマンドとその説明です。",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="🔹 !creategroup",
            value="VC参加者のためのグループ（個別/共有）チャンネルを作成します。\n例: `!creategroup vc名`",
            inline=False
        )

        embed.add_field(
            name="🔹 !setupvc",
            value="VCに連動してチャンネルを自動作成・削除する設定を行います。\n例: `!setupvc #カテゴリ名`",
            inline=False
        )

        embed.add_field(
            name="🔹 !vctimer <分数>",
            value="ボイスチャンネルで指定した時間のタイマーを開始します。\n例: `!vctimer 15`",
            inline=False
        )

        embed.add_field(
            name="🔹 !vote @対象",
            value="匿名投票を開始します。DMで結果を送信します。\n例: `!vote @プレイヤー1 @プレイヤー2`",
            inline=False
        )

        embed.add_field(
            name="🔹 !shutdown",
            value="Botを安全にシャットダウンします（管理者限定）。\n例: `!shutdown`",
            inline=False
        )

        embed.add_field(
            name="🔹 !restart",
            value="Botを再起動します（管理者限定）。\n例: `!restart`",
            inline=False
        )

        embed.set_footer(text="💡 各コマンドの引数は状況に応じて調整してください。")

        await ctx.send(embed=embed)

# 🔧 discord.py 2.x 対応の setup（非同期）
async def setup(bot):
    await bot.add_cog(HelpMe(bot))
