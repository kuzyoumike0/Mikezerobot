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

        #mimic test        
        try:
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

        #mimic test
        except Exception as e:
            # 発生した例外のメッセージをDiscordに送信
            await ctx.send(f"エラーが発生しました: {e}")

#mimic test
class PetView(View):
    PET_IMAGE_URL = "https://raw.githubusercontent.com/kuzyoumike0/Mikezerobot/main/images/pet_fuwafuwa_happy.png"
    #ペットイメージのURL指定

    def __init__(self, bot, user):
        super().__init__()
        self.bot = bot
        self.user = user

        # --- 表示用性格ボタン（disabled） ---
        personalities = ["キラキラ", "カチカチ", "もちもち", "ふわふわ"]
        for p in personalities:
            self.add_item(Button(label=p, style=discord.ButtonStyle.secondary, disabled=True))

        # --- アクションボタン（撫でる・散歩） ---
        self.add_item(NadeButton())  # 撫でる
        self.add_item(SanpoButton())  # 散歩

    def load_pet(self):
        try:
            with open("data/pets.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "personality": "ふわふわ",
                "mood": 50,
                "exp": {"feed": 0, "walk": 0}
            }

    def save_pet(self, pet_data):
        with open("data/pets.json", "w", encoding="utf-8") as f:
            json.dump(pet_data, f, ensure_ascii=False, indent=2)

# mimic test
async def setup(bot):
    await bot.add_cog(PetGame(bot))

# 以下、PetView クラスを同ファイル内に記述し View ボタン・JSON保存処理を保持
# bot = commands.Bot(command_prefix="!", intents=intents)
# bot.load_extension("cogs.petgame") で cog 登録して運用
