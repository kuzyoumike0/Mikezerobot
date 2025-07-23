import discord
from discord.ext import commands
from discord.ui import Button, View
from collections import defaultdict

# 投票セッションを保持する辞書
vote_sessions = {}


class VoteButton(Button):

    def __init__(self, label, vote_id):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.vote_id = vote_id

    async def callback(self, interaction: discord.Interaction):
        data = vote_sessions.get(self.vote_id)
        if not data:
            await interaction.response.send_message("この投票は終了しています。",
                                                    ephemeral=True)
            return

        # 投票数を増やす
        data["votes"][self.label] += 1
        await interaction.response.send_message("✅ あなたの投票を受け付けました（匿名）",
                                                ephemeral=True)


class Vote(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def startvote(self, ctx, *, text):
        try:
            parts = text.split("|")
            question = parts[0].strip()
            options = [opt.strip() for opt in parts[1:]]
            if len(options) < 2:
                await ctx.send("最低でも2つの選択肢が必要です。")
                return
        except:
            await ctx.send("形式は `!startvote 質問 | 選択肢1 | 選択肢2 | ...` です。")
            return

        view = View()
        vote_id = ctx.message.id
        vote_sessions[vote_id] = {
            "question": question,
            "options": options,
            "votes": defaultdict(int)
        }

        for opt in options:
            view.add_item(VoteButton(opt, vote_id))

        embed = discord.Embed(title="🗳 匿名投票",
                              description=question,
                              color=0x3498db)
        for i, opt in enumerate(options, start=1):
            embed.add_field(name=f"{i}. {opt}",
                            value="クリックしてDMで投票",
                            inline=False)

        # ギルドメンバーにDMで送信
        for member in ctx.guild.members:
            if not member.bot:
                try:
                    await member.send(embed=embed, view=view)
                except discord.Forbidden:
                    pass

        await ctx.send("📬 メンバーに匿名投票をDMで送信しました。")

    @commands.command()
    async def resultvote(self, ctx, message_id: int):
        data = vote_sessions.get(message_id)
        if not data:
            await ctx.send("その投票は見つかりません。")
            return

        result_text = f"📊 **{data['question']}** の結果：\n"
        for option in data["options"]:
            result_text += f"・{option}: {data['votes'][option]}票\n"

        await ctx.send(result_text)
        # 投票データ削除（任意）
        del vote_sessions[message_id]


async def setup(bot):
    await bot.add_cog(Vote(bot))
