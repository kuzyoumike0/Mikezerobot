import discord
from discord.ext import commands
import json
import os
from datetime import datetime

from config import MYSTERY_CHANNEL_ID, MYSTERY_SET_CHANNEL_ID  # 出題・登録用チャンネルID

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
        """現在の謎を指定チャンネルに表示します。"""
        data = load_mystery_data()
        current = data["current"]
        if not current:
            await ctx.send("🕵️ 現在出題中の謎はありません。")
            return

        embed = discord.Embed(
            title=f"🔍 謎 No.{current['id']}：{current['title']}",
            description=current['question'],
            color=discord.Color.dark_blue()
        )
        embed.set_footer(text="答えが分かったら `!answer <答え>`")

        channel = self.bot.get_channel(MYSTERY_CHANNEL_ID)
        if channel is None:
            await ctx.send("⚠️ 出題チャンネルが見つかりません。config.py を確認してください。")
            return

        await channel.send(embed=embed)
        await ctx.send(f"📨 謎は <#{MYSTERY_CHANNEL_ID}> に投稿されました。")

    @commands.command(name="answer")
    async def answer(self, ctx, *, user_answer: str):
        """謎への回答を送信します。正誤判定されます。"""
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
            data.setdefault("solved", {}).setdefault(str(current["id"]), []).append(user_id)
            save_mystery_data(data)
            await ctx.send(f"🎉 正解です！お見事、{ctx.author.mention} 探偵！")
        else:
            await ctx.send("❌ 残念、不正解です。再挑戦できます。")

    @commands.command(name="set_mystery")
    @commands.has_permissions(administrator=True)
    async def set_mystery(self, ctx, title: str, answer: str, *, question: str):
        """管理者用：新しい謎をセットして出題します。"""
        if ctx.channel.id != MYSTERY_SET_CHANNEL_ID:
            await ctx.send(f"❌ このコマンドは <#{MYSTERY_SET_CHANNEL_ID}> チャンネルでのみ実行可能です。")
            return

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

        embed = discord.Embed(
            title=f"🧩 新しい謎 No.{mystery_id}：{title}",
            description=question,
            color=discord.Color.purple()
        )
        embed.set_footer(text="答えが分かったら `!answer <答え>`")

        channel = self.bot.get_channel(MYSTERY_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
            await ctx.send(f"📨 謎を <#{MYSTERY_CHANNEL_ID}> に出題しました。")
        else:
            await ctx.send("⚠️ 謎はセットされましたが、出題チャンネルが見つかりません。")

    @set_mystery.error
    async def set_mystery_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("⚠️ このコマンドを実行するには管理者権限が必要です。")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ 引数が不足しています。`!set_mystery <タイトル> <正解> <問題文>` の形式で入力してください。")
        else:
            await ctx.send(f"⚠️ コマンド実行中にエラーが発生しました：{error}")

    @commands.command(name="close_mystery")
    @commands.has_permissions(administrator=True)
    async def close_mystery(self, ctx):
        """現在の謎を終了させます。"""
        data = load_mystery_data()
        if not data["current"]:
            await ctx.send("🔒 現在アクティブな謎はありません。")
            return
        data["current"] = None
        save_mystery_data(data)
        await ctx.send("🔒 現在の謎を終了しました。")

    @commands.command(name="helpme_mystery")
    async def helpme_mystery(self, ctx):
        """このCogで使用できるコマンド一覧を表示します。"""
        embed = discord.Embed(
            title="🔎 MysteryGame コマンド一覧",
            description="このBotで利用できる謎解き関連コマンドです。",
            color=discord.Color.teal()
        )
        embed.add_field(
            name="!mystery",
            value="現在出題中の謎を表示（指定チャンネルに投稿）",
            inline=False
        )
        embed.add_field(
            name="!answer <答え>",
            value="謎への回答を送信（正誤判定あり）",
            inline=False
        )
        embed.add_field(
            name="!set_mystery <タイトル> <正解> <問題文>",
            value=f"🛠 管理者専用：新しい謎を登録して出題（<#{MYSTERY_SET_CHANNEL_ID}> チャンネル限定）",
            inline=False
        )
        embed.add_field(
            name="!close_mystery",
            value="🛠 管理者専用：現在の謎を締め切る",
            inline=False
        )
        embed.set_footer(text="※ 謎は定期的に更新されます。出題内容を見逃すな！")
        await ctx.send(embed=embed)

# Bot にこの Cog を登録
async def setup(bot):
    await bot.add_cog(MysteryGame(bot))
