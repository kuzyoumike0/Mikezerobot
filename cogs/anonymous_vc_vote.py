import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from collections import defaultdict

class AnonymousVCVote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vote_sessions = {}  # {guild_id: {"question": str, "options": [str], "votes": {user_id: index}, "participants": [user]}}
    
    @app_commands.command(name="start_vote_vc", description="VC参加者に匿名投票を送信します")
    async def start_vote_vc(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("ボイスチャンネルに参加してからコマンドを使ってください。", ephemeral=True)
            return
        
        await interaction.response.send_message("DMにて投票内容を設定してください。", ephemeral=True)
        
        def check_dm(m):
            return m.author == interaction.user and isinstance(m.channel, discord.DMChannel)

        try:
            await interaction.user.send("📋 投票の質問を入力してください：")
            question_msg = await self.bot.wait_for("message", check=check_dm, timeout=60)
            question = question_msg.content.strip()

            await interaction.user.send("📝 選択肢をカンマ区切りで入力してください（最大5つ）：")
            options_msg = await self.bot.wait_for("message", check=check_dm, timeout=60)
            options = [opt.strip() for opt in options_msg.content.split(",")][:5]

            if len(options) < 2:
                await interaction.user.send("選択肢は2つ以上必要です。")
                return
        except asyncio.TimeoutError:
            await interaction.user.send("⏱️ 時間切れです。最初からやり直してください。")
            return

        vc_members = [member for member in interaction.user.voice.channel.members if not member.bot]
        self.vote_sessions[interaction.guild.id] = {
            "question": question,
            "options": options,
            "votes": {},
            "participants": vc_members,
            "owner_id": interaction.user.id
        }

        for member in vc_members:
            try:
                view = VoteButtons(self, member.id, interaction.guild.id)
                await member.send(f"【匿名投票】\n{question}\n\n" + "\n".join(
                    [f"{i+1}. {opt}" for i, opt in enumerate(options)]), view=view)
            except:
                pass

        await interaction.user.send(f"✅ VC参加者 {len(vc_members)} 人に匿名投票を送信しました。\n締め切るには `/end_vote` を使ってください。")

    @app_commands.command(name="end_vote", description="投票を締め切り、結果を表示します")
    async def end_vote(self, interaction: discord.Interaction):
        session = self.vote_sessions.get(interaction.guild.id)
        if not session or session["owner_id"] != interaction.user.id:
            await interaction.response.send_message("現在あなたが管理している投票はありません。", ephemeral=True)
            return

        votes = session["votes"]
        options = session["options"]
        result_count = defaultdict(int)

        for idx in votes.values():
            result_count[idx] += 1

        result_text = f"📊 投票結果：{session['question']}\n\n"
        sorted_results = sorted(result_count.items(), key=lambda x: -x[1])

        for idx, count in sorted_results:
            result_text += f"🥇 {options[idx]}：{count}票\n"
        for i in range(len(options)):
            if i not in result_count:
                result_text += f"{options[i]}：0票\n"

        del self.vote_sessions[interaction.guild.id]

        await interaction.user.send(result_text)
        await interaction.response.send_message("✅ 結果をDMで送信しました。", ephemeral=True)

class VoteButtons(discord.ui.View):
    def __init__(self, cog: AnonymousVCVote, user_id: int, guild_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.user_id = user_id
        self.guild_id = guild_id
        session = cog.vote_sessions[guild_id]
        for i, opt in enumerate(session["options"]):
            self.add_item(VoteButton(label=f"{i+1}", index=i))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

class VoteButton(discord.ui.Button):
    def __init__(self, label, index):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        session = self.view.cog.vote_sessions.get(self.view.guild_id)
        if session:
            session["votes"][interaction.user.id] = self.index
            await interaction.response.send_message("✅ 投票を受け付けました（匿名）", ephemeral=True)
            self.view.disable_all_items()
            await interaction.message.edit(view=self.view)

async def setup(bot):
    await bot.add_cog(AnonymousVCVote(bot))
