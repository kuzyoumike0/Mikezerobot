import discord
from discord.ext import commands
import json
import os
import asyncio

TEMPLATE_DATA_PATH = "data/template_messages.json"

# テンプレートを送るチャンネルID
TEMPLATE_CHANNEL_ID = 1388730912396804106

MESSAGE_1 = "↓テンプレートとしてお使いください。"
MESSAGE_2 = (
    "------------------------\n"
    "１．名前（HN・読み方も）\n"
    "２．最近あったできごと・自己紹介\n"
    "３．GMかPLか\n"
    "４．おすすめシナリオ\n"
    "５．性別\n"
    "------------------------"
)


class TemplateKeeper(commands.Cog):
    """指定チャンネルにテンプレートメッセージを常に最下部に表示し続けるコグ。
    誰かがメッセージを送るたびに古いテンプレートを削除して再送信する。
    """

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        asyncio.create_task(self._init_template())

    async def _init_template(self):
        await self.bot.wait_until_ready()
        await self.ensure_template()

    # ---------------- 永続化 ----------------
    def load_data(self) -> dict:
        if not os.path.exists(TEMPLATE_DATA_PATH):
            return {"msg1_id": None, "msg2_id": None}
        try:
            with open(TEMPLATE_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"msg1_id": None, "msg2_id": None}

    def save_data(self, data: dict):
        os.makedirs(os.path.dirname(TEMPLATE_DATA_PATH), exist_ok=True)
        with open(TEMPLATE_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # ---------------- テンプレート送信・削除 ----------------
    async def delete_old_template(self, channel: discord.TextChannel):
        """保存済みのテンプレートメッセージIDがあれば削除する"""
        data = self.load_data()
        for key in ("msg1_id", "msg2_id"):
            mid = data.get(key)
            if mid:
                try:
                    msg = await channel.fetch_message(mid)
                    await msg.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass  # 既に削除済みなら無視
        self.save_data({"msg1_id": None, "msg2_id": None})

    async def send_template(self, channel: discord.TextChannel):
        """テンプレートを2通送信してIDを保存する"""
        msg1 = await channel.send(MESSAGE_1)
        msg2 = await channel.send(MESSAGE_2)
        self.save_data({"msg1_id": msg1.id, "msg2_id": msg2.id})

    async def ensure_template(self):
        """起動時にテンプレートが存在するか確認し、なければ送信する"""
        channel = self.bot.get_channel(TEMPLATE_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            print(f"[TemplateKeeper] チャンネルID {TEMPLATE_CHANNEL_ID} が見つかりません。")
            return

        data = self.load_data()
        # 既存のメッセージが生きているか確認
        if data.get("msg1_id") and data.get("msg2_id"):
            try:
                await channel.fetch_message(data["msg1_id"])
                await channel.fetch_message(data["msg2_id"])
                print("[TemplateKeeper] 既存のテンプレートメッセージを確認しました。")
                return  # 両方存在すれば再送不要
            except (discord.NotFound, discord.HTTPException):
                pass  # どちらかが消えていたら再送する

        await self.delete_old_template(channel)
        await self.send_template(channel)
        print("[TemplateKeeper] テンプレートメッセージを送信しました。")

    # ---------------- メッセージ監視 ----------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bot自身のメッセージは無視（無限ループ防止）
        if message.author.bot:
            return

        # 対象チャンネル以外は無視
        if message.channel.id != TEMPLATE_CHANNEL_ID:
            return

        channel = message.channel
        await self.delete_old_template(channel)
        await self.send_template(channel)


async def setup(bot):
    await bot.add_cog(TemplateKeeper(bot))
