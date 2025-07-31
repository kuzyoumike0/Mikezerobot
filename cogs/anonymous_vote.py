import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
from collections import defaultdict

class AnonymousVote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vote_sessions = {}  # {message_id: {"options": [...], "votes": {user_id: option}, "owner_id": int}}

    @app_commands.command(name="anonymous_vote", description="VC参加者限定で匿名投票を開始します")
    @app_commands.describe(question="投票の質問", options="カンマ区切りで選択肢を入力（例: A,B,C）")
    async def anonymous_vote(self, interaction: discord.Interaction, question: str, options: str):
        author = interaction.user
        voice_state = author.voice
        if not voice_state or not voice_state.channel:
            await interaction.response.send_message("VCに参加している必要があります。", ephemeral=True)
            return

        vc_members = [m for m in voice_state.channel.members if not m.bot]
        if len(vc_members) < 1:
            await interaction.response.send_message("VCに他の参加者がいません。", ephemeral=True)
            return

        option_list = [opt.strip() for opt in options.split(",") if opt.strip()]
        if len(option_list) < 2:
            await interaction.response.send_message("少なくとも2つの選択肢が必要です。", ephemeral=True)
            return

        embed = discord.Embed(title="匿名投票", description=question, color=discord.Color.blue())
        for idx, opt in enumerate(option_list, start=1):
            embed.add_field(name=f"{idx}. {opt}", value="\u200b", inline=False)

        class VoteSelect(Select):
            def __init__(self, options_list, members, vote_sessions, message_id_ref):
                self.members = members
                self.vote_sessions = vote_sessions
                self.message_id_ref = message_id_ref
                select_options = [
                    discord.SelectOption(label=f"{i+1}. {opt}", value=str(i))
                    for i, opt in enumerate(options_list)
                ]
                super().__init__(placeholder="選択肢を選んでください", min_values=1, max_values=1, options=select_options)

            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id not in [m.id for m in self.members]:
                    await interaction.response.send_message("あなたはVCに参加していないため投票できません。", ephemeral=True)
                    return

                selected = int(self.values[0])
                message_id = self.message_id_ref[0]
                self.vote_sessions[message_id]["votes"][interaction.user.id] = selected
                await interaction.response.send_message("投票を受け付けました。", ephemeral=True)

        message = await interaction.channel.send(
            embed=embed,
            view=View(VoteSelect(option_list, vc_members, self.vote_sessions, [0]))
        )
        self.vote_sessions[message.id] = {
            "options": option_list,
            "votes": {},
            "owner_id": author.id,
            "question": question
        }
        # 後でID参照用にmessage_id格納
        for item in message.components[0].children:
            if isinstance(item, Select):
                item.message_id_ref[0] = message.id

        await interaction.response.send_message(f"匿名投票を開始しました。", ephemeral=True)

    @app_commands.command(name="vote_result", description="自分が作成した投票の結果をDMで確認します")
    async def vote_result(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        found = False
        for msg_id, session in self.vote_sessions.items():
            if session["owner_id"] == user_id:
                found = True
                total = defaultdict(int)
                for uid, sel in session["votes"].items():
                    total[sel] += 1
                result_text = f"**質問**: {session['question']}\n\n"
                for i, opt in enumerate(session["options"]):
                    count = total.get(i, 0)
                    result_text += f"{i+1}. {opt}: {count}票\n"
                await interaction.user.send(result_text)
                await interaction.response.send_message("DMで結果を送信しました。", ephemeral=True)
                break
        if not found:
            await interaction.response.send_message("あなたが作成した投票が見つかりません。", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AnonymousVote(bot))
