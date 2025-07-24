import discord
from discord.ext import commands
import json
import os
from datetime import datetime

DATA_PATH = "data/mysteries.json"

def load_mystery_data():
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump({"current": None, "history": [], "solved": {}}, f, indent=4)
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_mystery_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class MysteryGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="mystery")
    async def show_mystery(self, ctx):
        """現在の謎を表示します"""
        data = load_mystery_data()
        current = data["current"]
        if not current:
            await ctx.send("🕵️ 現在出題中の謎はありません。")
            return

        embed = discord.Embed(title=f"🔍 謎 No.{current['id']}：{current['title']}",
                              description=current['question'],
                              color=discord.Color.dark_blue())
        embed.set_footer(text="答えが分かったら `/answer <答え>`")
        await ctx.send(embed=embed)

    @commands.command(name="answer")
    async def answer(self, ctx, *, user_answer: str):
        """謎への回答を送信します"""
        data = load_mystery_data()
        current = data["current"]
        if not current:
            await ctx.send("🕵️ 現在出題中の謎はありません。")
            return

        user_id = str(ctx.author.id)
        if user_id in data["solved"].get(str(current["id"]), []):
            await ctx.send("✅ すでに正解済みです。")
            return

        if user_answer.strip().lower() == current["answer"].strip().lower():
            # 正解
            data.setdefault("solved", {}).setdefault(str(current["id"]), []).append(user_id)
            save_mystery_data(data)
            await ctx.send(f"🎉 正解です！お見事、{ctx.author.mention} 探偵！")
        else:
            await ctx.send("❌ 残念、不正解です。再挑戦できます。")

    @commands.command(name="set_mystery")
    @commands.has_permissions(administrator=True)
    async def set_mystery(self, ctx, title: str, answer: str, *, question: str):
        """管理者用：新しい謎をセット"""
        data = load_mystery_data()
        mystery_id = len(data["history"]) + 1
        new_mystery = {
            "id": mystery_id,
            "title": title,
            "question": question,
            "answer": answer
        }
        data["current"] = new_mystery
        data["history"].append(new_mystery)
        save_mystery_data(data)
        await ctx.send(f"🧩 謎 No.{mystery_id}「{title}」をセットしました。")

    @commands.command(name="close_mystery")
    @commands.has_permissions(administrator=True)
    async def close_mystery(self, ctx):
        """管理者用：現在の謎を終了します"""
        data = load_mystery_data()
        if not data["current"]:
            await ctx.send("現在アクティブな謎はありません。")
            return
        data["current"] = None
        save_mystery_data(data)
        await ctx.send("🔒 現在の謎を終了しました。")

    @commands.command(name="mystery_rank")
    async def mystery_rank(self, ctx):
        """正解数ランキングを表示します"""
        data = load_mystery_data()
        solved = data.get("solved", {})
        score = {}
        for ids in solved.values():
            for uid in ids:
                score[uid] = score.get(uid, 0) + 1
        if not score:
            await ctx.send("まだ誰も謎を解いていません。")
            return

        sorted_users = sorted(score.items(), key=lambda x: x[1], reverse=True)
        description = ""
        for i, (uid, count) in enumerate(sorted_users[:10], start=1):
            user = await self.bot.fetch_user(int(uid))
            description += f"{i}. {user.name} - {count}問正解\n"

        embed = discord.Embed(title="🏆 名探偵ランキング", description=description, color=discord.Color.gold())
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MysteryGame(bot))
