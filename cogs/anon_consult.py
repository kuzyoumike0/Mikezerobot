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

    def generate_anon_id(self, ctx=None):
        index = self.data["counter"]

        letter_index = index // 100  # 0〜25（A〜Z）
        number = (index % 100) + 1   # 1〜100

        if letter_index >= 26:
            # カウンターが上限を超えた場合、DMで通知する（ctxがあれば）
            if ctx:
                asyncio.create_task(self.send_limit_warning(ctx.author))
            # ループさせず最大の匿名IDを返す
            letter_index = 25
            number = 100

        letter = chr(65 + letter_index)  # A〜Z
        anon_id = f"匿名{letter}{number}さん"

        self.data["counter"] += 1
        self.save_data()
        return anon_id

    async def send_limit_warning(self, member):
        try:
            await member.send(
                "⚠️ 匿名IDが最大の組み合わせ（匿名Z100さん）に達しました。これ以上の匿名IDは発行できません。"
            )
        except Exception:
            pass

    def is_dm(self, ctx):
        return isinstance(ctx.channel, discord.DMChannel)

    @commands.command(name="anon相談")
    async def anon_consult(self, ctx: commands.Context, *, content: str):
        if not self.is_dm(ctx):
            await ctx.send("❌ このコマンドはDMでのみ使用してください。")
            return

        channel = self.bot.get_channel(ANON_CHANNEL_ID)
        if channel is None:
            await ctx.send("❌ 投稿チャンネルが見つかりません。管理者に連絡してください。")
            return

        anon_id = self.generate_anon_id(ctx)
        message = f"💬 **{anon_id} の相談**\n{content}"

        posted_msg = await channel.send(message)
        thread = await posted_msg.create_thread(name=f"{anon_id} の相談スレッド")

        # 匿名IDをキーにして保存
        self.data["consults"][anon_id] = {
            "thread_id": thread.id
        }
        self.save_data()

        await ctx.send(f"✅ 匿名相談を投稿しました！あなたの匿名IDは **{anon_id}** です。返信時にこの名前を使ってください。")

    @commands.command(name="anon返信")
    async def anon_reply(self, ctx: commands.Context, anon_id: str, *, reply: str):
        if not self.is_dm(ctx):
            await ctx.send("❌ このコマンドはDMでのみ使用してください。")
            return

        if anon_id not in self.data["consults"]:
            await ctx.send(f"❌ 匿名ID「{anon_id}」の相談が見つかりませんでした。")
            return

        thread_id = self.data["consults"][anon_id]["thread_id"]
        thread = self.bot.get_channel(thread_id)
        if thread is None:
            await ctx.send("❌ スレッドが見つかりませんでした。")
            return

        reply_anon_id = self.generate_anon_id(ctx)

        await thread.send(f"🗨️ **{reply_anon_id} より返信：**\n{reply}")
        await ctx.send(f"✅ 匿名で返信しました！あなたの匿名IDは **{reply_anon_id}** です。")

    @commands.command(name="soudanhelp")
    async def soudan_help(self, ctx: commands.Context):
        if not self.is_dm(ctx):
            await ctx.send("❌ このコマンドはDMでのみ使用してください。")
            return

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
            name="!anon返信 <匿名ID> <返信内容>",
            value="匿名IDを指定して相談に匿名で返信します。返信は専用スレッドに投稿されます。",
            inline=False
        )
        embed.set_footer(text="匿名相談Botをご利用いただきありがとうございます！")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AnonConsult(bot))
