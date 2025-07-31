import discord
from discord.ext import commands
from discord import app_commands
from config import GUILD_ID

class AnonymousVoteView(discord.ui.View):
    def __init__(self, user_id, options, vote_manager):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.vote_manager = vote_manager
        for idx, option in enumerate(options, start=1):
            self.add_item(AnonymousVoteButton(str(idx), option, vote_manager, user_id))

class AnonymousVoteButton(discord.ui.Button):
    def __init__(self, label, option, vote_manager, user_id):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.option = option
        self.vote_manager = vote_manager
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if self.vote_manager.has_voted(self.user_id):
            await interaction.response.send_message("すでに投票しています。", ephemeral=True)
            return

        self.vote_manager.add_vote(self.user_id, self.option)
        await interaction.response.send_message("✅ 投票を受け付けました！", ephemeral=True)

class VoteSession:
    def __init__(self, question, options):
        self.question = question
        self.options = options
        self.votes = {}  # user_id: option

    def add_vote(self, user_id, option):
        self.votes[user_id] = option

    def has_voted(self, user_id):
        return user_id in self.votes

    def get_results(self):
        from collections import Counter
        return Counter(self.votes.values())

class AnonymousVote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vote_session = None

    @app_commands.command(name="start_vote", description="匿名投票を開始（VC参加者へDMを送る）")
    @app_commands.describe(question="質問内容", options="カンマ区切りの選択肢（例: 1番,2番,3番）")
    async def start_vote(self, interaction: discord.Interaction, question: str, options: str):
        if self.vote_session is not None:
            await interaction.response.send_message("⚠️ すでに投票が実施中です。", ephemeral=True)
            return

        option_list = [opt.strip() for opt in options.split(",")]
        self.vote_session = VoteSession(question, option_list)

        # VC参加者取得
        vc = interaction.user.voice
        if vc is None or vc.channel is None:
            await interaction.response.send_message("⚠️ VCに参加していません。", ephemeral=True)
            self.vote_session = None
            return

        members = [m for m in vc.channel.members if not m.bot]

        sent_count = 0
        for member in members:
            try:
                dm = await member.create_dm()
                embed = discord.Embed(
                    title="🗳 匿名投票",
                    description=f"**{question}**\n選択肢から一つ選んでください。",
                    color=discord.Color.blue()
                )
                for idx, opt in enumerate(option_list, start=1):
                    embed.add_field(name=f"{idx}.", value=opt, inline=False)
                view = AnonymousVoteView(member.id, option_list, self.vote_session)
                await dm.send(embed=embed, view=view)
                sent_count += 1
            except:
                pass

        await interaction.response.send_message(f"✅ 投票を開始しました。DMを送信：{sent_count}人", ephemeral=True)

    @app_commands.command(name="end_vote", description="投票を終了して集計結果を表示")
    async def end_vote(self, interaction: discord.Interaction):
        if self.vote_session is None:
            await interaction.response.send_message("⚠️ 現在実施中の投票はありません。", ephemeral=True)
            return

        results = self.vote_session.get_results()
        result_text = "\n".join(f"{opt}: {count}票" for opt, count in results.items())

        embed = discord.Embed(
            title="📊 投票結果",
            description=result_text or "投票がありませんでした。",
            color=discord.Color.green()
        )
        await interaction.user.send(embed=embed)
        self.vote_session = None
        await interaction.response.send_message("✅ 集計結果をDMに送信しました。", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        guild = discord.Object(id=GUILD_ID)
        self.bot.tree.copy_global_to(guild=guild)
        await self.bot.tree.sync(guild=guild)
        print("✅ Slash commands synced.")

async def setup(bot):
    await bot.add_cog(AnonymousVote(bot))
