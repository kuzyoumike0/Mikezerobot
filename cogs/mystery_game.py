import discord
from discord.ext import commands
import json
import os
import random
import shlex
from config import MYSTERY_CHANNEL_ID, MYSTERY_SET_CHANNEL_ID

MYSTERY_FILE = "data/mysteries.json"

class MysteryGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_mystery = None
        self.correct_users = set()

    def load_mysteries(self):
        if os.path.exists(MYSTERY_FILE):
            with open(MYSTERY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_mysteries(self, mysteries):
        with open(MYSTERY_FILE, "w", encoding="utf-8") as f:
            json.dump(mysteries, f, indent=4, ensure_ascii=False)

    @commands.command(name="set_mystery")
    async def set_mystery(self, ctx, *, args):
        if ctx.channel.id != MYSTERY_SET_CHANNEL_ID:
            return

        try:
            parts = shlex.split(args)
            if len(parts) < 3:
                await ctx.send("❌ 使用方法: `!set_mystery \"タイトル\" \"正解\" \"問題文\"`")
                return
            title, answer, question = parts[0], parts[1], " ".join(parts[2:])

            mysteries = self.load_mysteries()
            mysteries.append({
                "title": title,
                "answer": answer.lower(),
                "question": question
            })
            self.save_mysteries(mysteries)
            await ctx.send(f"✅ 謎「{title}」を登録しました。")

        except Exception as e:
            await ctx.send(f"❌ エラーが発生しました: {e}")

    @commands.command(name="mystery")
    async def mystery(self, ctx):
        if ctx.channel.id != MYSTERY_CHANNEL_ID:
            return

        mysteries = self.load_mysteries()
        if not mysteries:
            await ctx.send("⚠️ 謎が登録されていません。")
            return

        selected = random.choice(mysteries)
        self.current_mystery = selected
        self.correct_users.clear()

        embed = discord.Embed(
            title=f"🧩 謎：{selected['title']}",
            description=selected['question'],
            color=0x00ccff
        )
        await ctx.send(embed=embed)

    @commands.command(name="answer")
    async def answer(self, ctx, *, user_answer):
        if not self.current_mystery:
            await ctx.send("❌ 現在出題中の謎がありません。")
            return

        if ctx.author.id in self.correct_users:
            await ctx.send("✅ あなたはすでに正解しています！")
            return

        # 回答部分をスパイラーテキスト（モザイク）で表示
        if user_answer.lower().strip() == self.current_mystery["answer"]:
            self.correct_users.add(ctx.author.id)
            await ctx.send(f"🎉 正解！おめでとう、{ctx.author.display_name}さん！ 答え：||{user_answer}||")
        else:
            await ctx.send(f"{ctx.author.mention} の回答: ||{user_answer}|| ・・・残念、不正解です。")

    @commands.command(name="helpme")
    async def helpme(self, ctx):
        embed = discord.Embed(
            title="🔍 推理ゲームコマンド一覧",
            description="このBotで使用できるコマンドは以下の通りです。",
            color=discord.Color.green()
        )
        embed.add_field(name="!mystery", value="ランダムな謎を出題します（出題専用チャンネル限定）。", inline=False)
        embed.add_field(name="!answer <解答>", value="現在出題されている謎に回答します。", inline=False)
        embed.add_field(name='!set_mystery "タイトル" "正解" "問題文"', value="新しい謎を登録します（管理者用チャンネル限定）。", inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MysteryGame(bot))
