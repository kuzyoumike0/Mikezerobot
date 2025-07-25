import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
from datetime import datetime, timedelta

# 必要な定数は config.py で管理する想定
from config import FEED_TITLE_ROLES, PET_COMMAND_CHANNEL_ID, ROLE_TITLE_10, ROLE_TITLE_30, ROLE_TITLE_50

class PetGame(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # !pet コマンド本体
    @commands.command(name="pet")
    async def pet_command(self, ctx: commands.Context):
        if ctx.channel.id != PET_COMMAND_CHANNEL_ID:
            await ctx.send("このコマンドは指定チャンネルでのみ使用可能です。")
            return

        # Embed + View送信
        view = PetView(self.bot, ctx.author)
        pet = view.load_pet()
        total_exp = sum(pet.get("exp", {}).values())

        embed = discord.Embed(
            title="🐶 ミルクシュガーの育成",
            description=f"性格: {pet.get('personality', 'ふわふわ')}\n機嫌: {pet.get('mood', 50)}/100\n経験値: {total_exp}",
            color=discord.Color.pink()
        )
        embed.set_image(url=view.PET_IMAGE_URL)
        await ctx.send(embed=embed, view=view)

# 以下、PetView クラスを同ファイル内に記述し View ボタン・JSON保存処理を保持
# bot = commands.Bot(command_prefix="!", intents=intents)
# bot.load_extension("cogs.petgame") で cog 登録して運用
