import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, select
import random
import config

class AnonymousVoteView(View):
    def __init__(self, options, participants, author_dm, vote_id):
        super().__init__(timeout=None)
        self.vote_results = {}
        self.participants = participants
        self.author_dm = author_dm
        self.vote_id = vote_id
        self.select_menu = discord.ui.Select(
            placeholder="投票する選択肢を選んでください",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=f"{i+1}. {opt}", value=str(i))
                for i, opt in enumerate(options)
            ]
        )
        self.select_menu.callback = self.on_select
        self.add_item(self.select_menu)

    async def on_select(self, interaction: discord.Interaction):
        voter_id = interaction.user.id

        if voter_id not in self.participants:
            await interaction.response.send_message("あなたはVC参加者ではありません。", ephemeral=True)
            return

        if voter_id in self.vote_results:
            await interaction.response.send_message("すでに投票済みです。", ephemeral=True)
            return

        self.vote_results[voter_id] = self.select_menu.values[0]
        await interaction.response.send_message("投票を受け付けました。", ephemeral=True)

        # 全員投票済みか確認
        if len(self.vote_results) == len(self.participants):
            result_counts = {}
            for v in self.vote_results.values():
                result_counts[v] = result_counts.get(v, 0) + 1

            result_text = "🗳️ **投票結果**\n"
            for option in self.select_menu.options:
                count = result_counts.get(option.value, 0)
                result_text += f"- {option.label}: {count}票\n"

            await self.author_dm.send(result_text)

class AnonymousVote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="anonymous_vote")
    async def anonymous_vote(self, ctx, question: str, *choices: str):
        """VC参加者限定の匿名投票（セレクトメニュー形式）"""
        if len(choices) < 2 or len(choices) > 10:
            await ctx.send("選択肢は2〜10個まで指定してください。例: `!anonymous_vote 好きな色は？ 赤 青 緑`")
            return

        # VC参加者の取得
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("まずVCに参加してください。")
            return

        vc_channel = ctx.author.voice.channel
        participants = [member.id for member in vc_channel.members]

        # DM送信できるかチェック
        try:
            author_dm = await ctx.author.create_dm()
            await author_dm.send("✅ 投票を開始します。全員の投票が完了すると結果が届きます。")
        except discord.Forbidden:
            await ctx.send("DMを送信できません。DMを許可してください。")
            return

        embed = discord.Embed(
            title="匿名投票",
            description=f"**{question}**\n\n以下の選択肢から1つ選んでください（VC参加者限定）",
            color=discord.Color.blurple()
        )
        for i, choice in enumerate(choices):
            embed.add_field(name=f"{i+1}. {choice}", value="\u200b", inline=False)

        vote_id = random.randint(1000, 9999)
        view = AnonymousVoteView(choices, participants, author_dm, vote_id)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(AnonymousVote(bot))
