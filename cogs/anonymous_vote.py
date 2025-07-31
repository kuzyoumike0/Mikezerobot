import discord
from discord.ext import commands
from discord.utils import get
from collections import defaultdict

number_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

class VoteVC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vote_sessions = {}  # message_id: {emoji: option_text}
        self.vote_results = defaultdict(lambda: defaultdict(list))  # message_id: {emoji: [user_id]}
        self.vote_creators = {}  # message_id: author.id
        self.vote_vc_members = {}  # message_id: set(user.id)

    @commands.command(name="start_vote_vc")
    async def start_vote_vc(self, ctx, question, *options):
        """VC参加者限定の匿名投票を開始"""
        if not options or len(options) > len(number_emojis):
            return await ctx.send("選択肢は1〜10個まで指定してください。")

        # VCに接続しているメンバーを取得
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            return await ctx.send("VCに接続してからこのコマンドを実行してください。")
        
        vc_members = {member.id for member in ctx.author.voice.channel.members}

        # Embed 作成
        embed = discord.Embed(title="🔒 匿名投票（VC参加者限定）", color=discord.Color.green())
        embed.add_field(name="質問", value=question, inline=False)

        emoji_option_map = {}
        description = ""

        for i, option in enumerate(options):
            emoji = number_emojis[i]
            emoji_option_map[emoji] = option
            description += f"{emoji}：{option}\n"

        embed.add_field(name="選択肢", value=description, inline=False)
        message = await ctx.send(embed=embed)

        # リアクションを自動付与
        for emoji in emoji_option_map.keys():
            await message.add_reaction(emoji)

        self.vote_sessions[message.id] = emoji_option_map
        self.vote_creators[message.id] = ctx.author.id
        self.vote_vc_members[message.id] = vc_members

    @commands.command(name="end_vote_vc")
    async def end_vote_vc(self, ctx, message_id: int):
        """投票を終了し、集計結果をコマンド実行者にDMで送信"""
        if message_id not in self.vote_sessions:
            return await ctx.send("指定されたメッセージIDの投票が見つかりません。")

        if self.vote_creators.get(message_id) != ctx.author.id:
            return await ctx.send("この投票を終了できるのは投票を開始した本人だけです。")

        results = self.vote_results.get(message_id, {})
        options = self.vote_sessions[message_id]
        summary = "🗳️ **投票結果（匿名）**\n\n"

        total_votes = 0
        for emoji, option in options.items():
            count = len(results.get(emoji, []))
            total_votes += count
            summary += f"{emoji} {option}: {count}票\n"

        summary += f"\n✅ 総投票数: {total_votes}票"

        # DMに送信
        try:
            await ctx.author.send(summary)
            await ctx.send("✅ 集計結果をDMに送信しました。")
        except discord.Forbidden:
            await ctx.send("❌ DMを送れませんでした。DMの設定を確認してください。")

        # クリーンアップ
        del self.vote_sessions[message_id]
        del self.vote_results[message_id]
        del self.vote_creators[message_id]
        del self.vote_vc_members[message_id]

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        message_id = payload.message_id
        if message_id not in self.vote_sessions:
            return

        if payload.user_id == self.bot.user.id:
            return

        # VC参加者か確認
        vc_members = self.vote_vc_members.get(message_id, set())
        if payload.user_id not in vc_members:
            return  # VC参加者以外は無視

        emoji = str(payload.emoji)
        if emoji not in self.vote_sessions[message_id]:
            return

        # 同じユーザーの他のリアクションを削除（1票制）
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(message_id)
        for reaction in message.reactions:
            if str(reaction.emoji) != emoji:
                users = await reaction.users().flatten()
                if any(u.id == payload.user_id for u in users):
                    await reaction.remove(discord.Object(id=payload.user_id))

        # 投票記録
        if payload.user_id not in self.vote_results[message_id][emoji]:
            self.vote_results[message_id][emoji].append(payload.user_id)


async def setup(bot):
    await bot.add_cog(VoteVC(bot))
