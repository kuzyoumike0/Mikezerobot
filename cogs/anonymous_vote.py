import discord
from discord.ext import commands
from collections import Counter
import config

class AnonymousVoteVC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 投票セッション情報
        # {message_id: {"question": str, "guild_id": int, "choices": tuple, "votes": {user_id: emoji}}}
        self.vote_sessions = {}

    @commands.command(name="start_vote_vc")
    async def start_vote_vc(self, ctx, question: str, *choices):
        """
        VC参加者限定匿名投票を開始します。
        例）!start_vote_vc 質問文 ✅ ❌ 👍 👎
        """
        if len(choices) == 0:
            await ctx.send("❌ 投票の選択肢を最低1つ指定してください。")
            return

        # 投票メッセージ送信
        message = await ctx.send(
            f"🎤 **VC参加者限定匿名投票**\n**質問:** {question}\n\n" +
            "リアクションで回答してください。選択肢:\n" + " ".join(choices)
        )

        # 選択肢リアクションを追加
        for emoji in choices:
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                await ctx.send(f"⚠️ 「{emoji}」はリアクションに使えません。")
                return

        # セッションに保存
        self.vote_sessions[message.id] = {
            "question": question,
            "guild_id": ctx.guild.id,
            "choices": choices,
            "votes": {}
        }

    @commands.command(name="end_vote_vc")
    async def end_vote_vc(self, ctx, message_id: int):
        """
        投票終了＆コマンド実行者のDMに結果送信
        例）!end_vote_vc 123456789012345678
        """
        session = self.vote_sessions.get(message_id)
        if not session:
            await ctx.send("❌ 投票IDが見つかりません。")
            return

        count = Counter(session["votes"].values())
        total_votes = sum(count.values())
        result_text = (
            f"📊 **匿名投票結果**\n"
            f"📝 質問: {session['question']}\n\n" +
            "\n".join(f"{emoji}：{count[emoji]}票" for emoji in session["choices"]) +
            f"\n\n🧮 総投票数: {total_votes}票"
        )

        try:
            await ctx.author.send(result_text)
            await ctx.send("📩 結果をDMに送信しました。")
        except discord.Forbidden:
            await ctx.send("⚠️ DMを送信できません。DMを開放してください。")

        del self.vote_sessions[message_id]

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        session = self.vote_sessions.get(payload.message_id)
        if not session:
            return

        emoji = str(payload.emoji)
        if emoji not in session["choices"]:
            return

        guild = self.bot.get_guild(session["guild_id"])
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        # VC参加中かチェック
        if not member.voice or not member.voice.channel:
            return

        # 投票記録（上書き）
        session["votes"][payload.user_id] = emoji

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        session = self.vote_sessions.get(payload.message_id)
        if session and payload.user_id in session["votes"]:
            del session["votes"][payload.user_id]

async def setup(bot):
    await bot.add_cog(AnonymousVoteVC(bot))
