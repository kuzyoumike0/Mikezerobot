import discord
from discord.ext import commands
import json
import os
from config import ANON_CHANNEL_ID

DATA_PATH = "data/anon_consult_data.json"

class AnonConsult(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.load_data()

    def load_data(self):
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {"counter": 0, "consults": {}}

    def save_data(self):
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def generate_anon_id(self):
        index = self.data["counter"]
        anon_id = f"匿名{chr(65 + (index % 26))}さん"
        self.data["counter"] += 1
        return anon_id

    @commands.command(name="anon相談")
    async def anon_consult(self, ctx: commands.Context, *, content: str):
        channel = self.bot.get_channel(ANON_CHANNEL_ID)
        if channel is None:
            await ctx.send("❌ 投稿チャンネルが見つかりません。管理者に連絡してください。")
            return

        anon_id = self.generate_anon_id()
        message = f"💬 **{anon_id} の相談**\n{content}"

        posted_msg = await channel.send(message)
        thread = await posted_msg.create_thread(name=f"{anon_id} の相談スレッド")

        consult_id = str(posted_msg.id)
        self.data["consults"][consult_id] = {
            "anon_id": anon_id,
            "thread_id": thread.id
        }
        self.save_data()

        await ctx.send("✅ 匿名相談を投稿しました！")

    @commands.command(name="anon返信")
    async def anon_reply(self, ctx: commands.Context, message_id: str, *, reply: str):
        if message_id not in self.data["consults"]:
            await ctx.send("❌ そのIDの相談が見つかりませんでした。")
            return

        anon_id = self.generate_anon_id()
        thread_id = self.data["consults"][message_id]["thread_id"]

        thread = self.bot.get_channel(thread_id)
        if thread is None:
            await ctx.send("❌ スレッドが見つかりませんでした。")
            return

        await thread.send(f"🗨️ **{anon_id} より返信：**\n{reply}")
        await ctx.send("✅ 匿名で返信しました！")

    @commands.command(name="soudanhelp")
    async def soudan_help(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🤖 匿名相談Botの使い方",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="!anon相談 <相談内容>",
            value="匿名で相談を投稿します。相談は特定チャンネルに投稿され、専用スレッドが作成されます。",
            inline=False
        )
        embed.add_field(
            name="!anon返信 <相談メッセージのID> <返信内容>",
            value="指定した相談IDの相談に匿名で返信します。返信は専用スレッドに投稿されます。",
            inline=False
        )
        embed.set_footer(text="匿名相談Botをご利用いただきありがとうございます！")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(AnonConsult(bot))
