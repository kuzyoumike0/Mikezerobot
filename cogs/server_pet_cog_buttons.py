import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import json
import os
import datetime

PET_DATA_PATH = "data/pets.json"
IMAGE_FOLDER = "images"

# 経験値や行動に対応するポイント
ACTION_EXP = {
    "キラキラ": 10,
    "カチカチ": 10,
    "もちもち": 10,
    "ふわふわ": 10,
    "撫でる": 5,
    "散歩": 7,
}

class PetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_update.start()

    def cog_unload(self):
        self.daily_update.cancel()

    def load_pet_data(self):
        if not os.path.exists(PET_DATA_PATH):
            return {}
        with open(PET_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_pet_data(self, data):
        os.makedirs(os.path.dirname(PET_DATA_PATH), exist_ok=True)
        with open(PET_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_pet_image(self, personality, mood):
        # personality: "もちもち"など / mood: "happy", "angry", "neutral"
        filename = f"pet_{personality}_{mood}.png"
        return os.path.join(IMAGE_FOLDER, filename)

    def ensure_pet_exists(self, guild_id):
        pet_data = self.load_pet_data()
        if str(guild_id) not in pet_data:
            pet_data[str(guild_id)] = {
                "level": 1,
                "exp": 0,
                "personality": "まるまる",  # 初期性格
                "mood": "neutral",          # 初期機嫌
                "last_update": datetime.datetime.utcnow().isoformat(),
            }
            self.save_pet_data(pet_data)
        return pet_data

    @commands.command(name="pet")
    async def show_pet(self, ctx):
        pet_data = self.ensure_pet_exists(ctx.guild.id)
        pet = pet_data[str(ctx.guild.id)]

        personality = pet.get("personality", "まるまる")
        mood = pet.get("mood", "neutral")
        image_path = self.get_pet_image(personality, mood)

        embed = discord.Embed(title="あなたのペット", color=discord.Color.green())
        embed.add_field(name="性格", value=personality, inline=True)
        embed.add_field(name="機嫌", value=mood, inline=True)
        embed.add_field(name="レベル", value=str(pet["level"]), inline=True)

        file = discord.File(image_path, filename="pet.png")
        embed.set_image(url="attachment://pet.png")

        await ctx.send(embed=embed, file=file)

    @commands.command(name="feed")
    async def feed_pet(self, ctx, food_type: str):
        pet_data = self.ensure_pet_exists(ctx.guild.id)
        pet = pet_data[str(ctx.guild.id)]

        if food_type not in ACTION_EXP:
            await ctx.send("その餌はあげられません。")
            return

        gained_exp = ACTION_EXP[food_type]
        pet["exp"] += gained_exp

        # 機嫌変化（簡易的）
        if food_type in ["撫でる", "散歩"]:
            pet["mood"] = "happy"
        else:
            pet["mood"] = "neutral"

        # 仮に特定の餌で性格も変わる仕様（オプション）
        if food_type in ["キラキラ", "カチカチ", "もちもち", "ふわふわ"]:
            pet["personality"] = food_type

        # レベルアップ
        while pet["exp"] >= 100:
            pet["level"] += 1
            pet["exp"] -= 100

        self.save_pet_data(pet_data)
        await ctx.send(f"{food_type}をあげました！ 経験値 +{gained_exp}")

    @tasks.loop(hours=24)
    async def daily_update(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        if now.hour != 1:
            return  # JST 10時 = UTC 1時

        pet_data = self.load_pet_data()
        for guild_id, pet in pet_data.items():
            pet["mood"] = "neutral"
        self.save_pet_data(pet_data)

    @daily_update.before_loop
    async def before_daily(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(PetCog(bot))
