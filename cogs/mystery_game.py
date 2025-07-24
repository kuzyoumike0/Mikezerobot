import discord
from discord.ext import commands
import json
import os
import random
from config import MYSTERY_CHANNEL_ID, MYSTERY_SET_CHANNEL_ID

MYSTERY_DATA_FILE = "data/mysteries.json"

class MysteryGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mysteries = self.load_mysteries()
        self.current_mystery = None

    def load_mysteries(self):
        if not os.path.exists(MYSTERY_DATA_FILE):
            return []
        with open(MYSTERY_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_mysteries(self):
        with open(MYSTERY_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.mysteries, f, ensure_ascii=False, indent=2)

    @commands.command(name="set_mystery")
    @commands.has_permissions(administrator=True)
    async def set_mystery(self, ctx, title: str, answer: str, *, question: str):
        if ctx.channel.id != MYSTERY_SET_CHANNEL_ID:
            return

        new_mystery = {
            "title": title,
            "question": question,
            "answer": answer
        }
        self.mysteries.append(new_mystery)
        self.save_mysteries()
        await ctx.send(f"✅ 謎「{title}」を登録しました。")

    @commands.command(name="mystery")
    async def mystery(self, ctx):
        if ctx.channel.id != MYSTERY_CHANNEL_ID:
            return

        if not self.mysteries:
            await ctx.send("❌ 登録されている謎がありません。")
            return

        self.current_mystery = random.choice(self.mysteries)
        embed = discord.Embed(
            title=f"🔍 謎解き：{self.current_mystery['title']}",
            description=self.current_mystery['question'],
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

    @commands.command(name="answer")
    async def answer(self, ctx, *, user_input: str):
        if ctx.channel.id != MYSTERY_CHANNEL_ID:
            return

        # モザイク形式でなければ警告
        if not (user_input.startswith("||") and user_input.endswith("||")):
            await ctx.send("❌ 回答は `!answer||回答||` の形式で入力してください。")
            return

        user_answer = user_input[2:-2].strip()

        if not self.current_mystery:
            await ctx.send("現在、出題中の謎はありません。")
            return

        if user_answer.lower() == self.current_mystery['answer'].lower():
            await ctx.send(f"🎉 正解！ {ctx.author.mention}")
            self.current_mystery = None
        else:
            await ctx.send(f"❌ 不正解… {ctx.author.mention}")

    @commands.command(name="helpme")
    async def helpme(self, ctx):
        embed = discord.Embed(
            title="📘 推理・謎解きBot コマンド一覧",
            color=discord.Color.teal()
        )
        embed.add_field(
            name="!mystery",
            value="ランダムに謎を出題します（出題用チャンネル限定）",
            inline=False
        )
        embed.add_field(
            name="!answer||答え||",
            value="出題された謎に回答します（モザイク必須）",
            inline=False
        )
        embed.add_field(
            name='!set_mystery "タイトル" "答え" "問題文"',
            value="謎を追加します（セット用チャンネル限定・管理者のみ）",
            inline=False
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MysteryGame(bot))
