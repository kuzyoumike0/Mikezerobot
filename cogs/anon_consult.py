import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
from config import ANON_CHANNEL_ID  # ← ここでインポート

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
        anon_id = f"匿名{chr(65 + (index % 26))}さん"  # 匿名Aさん〜Zさんをループ
        self.data["counter"] += 1
        return anon_id

    @app_commands.command(name="anon相談", description="匿名で相談を投稿します")
    @app_commands.describe(content="相談内容を入力してください")
    async def anon_consult(self, interaction: discord.Interaction, content: str):
        await interaction.response.defer(ephemeral=True)

        channel = self.bot.get_channel(ANON_CHANNEL_ID)
        if channel is None:
            await interaction.followup.send("❌ 投稿チャンネルが見つかりません。", ephemeral=True)
            return

        anon_id = self.generate_anon_id()
        message = f"💬 **{anon_id} の相談**\n{content}"

        # 投稿とスレッド作成
        posted_msg = await channel.send(message)
        thread = await posted_msg.create_thread(name=f"{anon_id} の相談スレッド")

        # 保存
        consult_id = str(posted_msg.id)
        self.data["consults"][consult_id] = {
            "anon_id": anon_id,
            "thread_id": thread.id
        }
        self.save_data()

        await interaction.followup.send("✅ 匿名相談を投稿しました！", ephemeral=True)

    @app_commands.command(name="anon返信", description="匿名相談に匿名で返信します")
    @app_commands.describe(message_id="相談メッセージのID", reply="返信内容")
    async def anon_reply(self, interaction: discord.Interaction, message_id: str, reply: str):
        await interaction.response.defer(ephemeral=True)

        if message_id not in self.data["consults"]:
            await interaction.followup.send("❌ そのIDの相談が見つかりませんでした。", ephemeral=True)
            return

        anon_id = self.generate_anon_id()
        thread_id = self.data["consults"][message_id]["thread_id"]

        thread = self.bot.get_channel(thread_id)
        if thread is None:
            await interaction.followup.send("❌ スレッドが見つかりませんでした。", ephemeral=True)
            return

        await thread.send(f"🗨️ **{anon_id} より返信：**\n{reply}")
        await interaction.followup.send("✅ 匿名で返信しました！", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AnonConsult(bot))
