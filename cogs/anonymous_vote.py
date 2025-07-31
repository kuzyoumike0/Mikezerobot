import discord
from discord.ext import commands
from collections import Counter
import config

class AnonymousVoteVC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vote_sessions = {}  # message_id: {question, guild_id, votes}

    @commands.command(name="start_vote_vc")
    async def start_vote_vc(self, ctx, *, question: str):
        """
        VC参加者限定の匿名投票を開始します。
        使用例: !start_vote_vc 明日のイベントに参加しますか？
        """
        message = await ctx.send(
            f"🎤 **VC参加者限定匿名投票**\n{question}\n\n" +
            "\n".join(f"{e}：" for e in config.VOTE_EMOJIS)
        )
        for emoji in config.VOTE_EMOJIS:
            await message.add_reaction(emoji)

        self.vote_sessions[message.id] = {
            "question": question,
            "guild_id": ctx.guild.id,
            "votes": {}
        }

    @commands.command(name="end_vote_vc")
    async def end_vote_vc(self, ctx, message_id: int):
        """
        VC匿名投票を終了し、コマンドを打った人のDMに結果を送信します。
        使用例: !end_vote_vc 123456789012345678
        """
        session = self.vote_sessions.get(message_id)
        if not session:
            await ctx.send("❌ 指定された投票IDは見つかりません。")
            return

        count = Counter(session["votes"].values())
        total_votes = sum(count.values())
        result_text = (
            f"📊 **匿名投票の結果**\n"
            f"📝 質問: {session['question']}\n\n" +
            "\n".join(f"{emoji}：{count[emoji]}票" for emoji in config.VOTE_EMOJIS) +
            f"\n\n🧮 総投票数: {total_votes}票"
        )

        try:
            await ctx.author.send(result_text)
            await ctx.send("📩 投票結果をDMに送信しました。")
        except discord.Forbidden:
            await ctx.send("⚠️ 結果をDMで送信できませんでした。DMの受信を有効にしてください。")

        del self.vote_sessions[message_id]

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        session = self.vote_sessions.get(payload.message_id)
        if not session:
            return

        emoji = str(payload.emoji)
        if emoji not in config.VOTE_EMOJIS:
            return

        guild = self.bot.get_guild(session["guild_id"])
        member = guild.get_member(payload.user_id)
        if not member:
            return

        # VC参加チェック
        if not member.voice or not member.voice.channel:
            return

        # 投票を記録
        session["votes"][payload.user_id] = emoji

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        session = self.vote_sessions.get(payload.message_id)
        if session and payload.user_id in session["votes"]:
            del session["votes"][payload.user_id]


async def setup(bot):
    await bot.add_cog(AnonymousVoteVC(bot))
