import discord
from discord.ext import commands
import os
import datetime
import json

# 既存の設定・関数を前提とします
PET_DATA_PATH = "data/pets.json"
PET_IMAGES_PATH = "images"

IMAGE_FILES = {
    "もちもち": "pet_mochimochi.png",
    "カチカチ": "pet_kachikachi.png",
    "キラキラ": "pet_kirakira.png",
    "ふわふわ": "pet_fuwafuwa.png",
}

PERSONALITY_MAP = {
    "キラキラ": "キラキラ",
    "カチカチ": "カチカチ",
    "もちもち": "もちもち",
    "ふわふわ": "まるまる"
}

EVOLVE_THRESHOLD = 100
EVOLVE_ORDER = ["もちもち", "カチカチ", "キラキラ", "ふわふわ"]

def load_pet_data():
    if not os.path.exists(PET_DATA_PATH):
        return {}
    with open(PET_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_pet_data(data):
    os.makedirs(os.path.dirname(PET_DATA_PATH), exist_ok=True)
    with open(PET_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def check_and_update_evolution(pet_data, guild_id):
    data = pet_data[guild_id]
    feed_counts = {k: data.get(f"feed_{k}", 0) for k in IMAGE_FILES.keys()}
    total_feed = sum(feed_counts.values())

    now = datetime.datetime.utcnow()
    last_change_str = data.get("last_image_change", "1970-01-01T00:00:00")
    last_change = datetime.datetime.fromisoformat(last_change_str)
    if (now - last_change).total_seconds() < 3600:
        return

    if total_feed >= EVOLVE_THRESHOLD:
        max_feed_type = None
        max_feed_count = -1
        for kind in EVOLVE_ORDER:
            if feed_counts[kind] > max_feed_count:
                max_feed_count = feed_counts[kind]
                max_feed_type = kind

        if max_feed_type:
            data["current_image"] = IMAGE_FILES[max_feed_type]
            data["personality"] = PERSONALITY_MAP.get(max_feed_type, "普通")
            for kind in IMAGE_FILES.keys():
                data[f"feed_{kind}"] = max(0, data.get(f"feed_{kind}", 0) - EVOLVE_THRESHOLD)
            data["last_image_change"] = now.isoformat()
            save_pet_data(pet_data)

class PetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pet")
    async def pet(self, ctx):
        guild_id = str(ctx.guild.id)
        pet_data = load_pet_data()

        if guild_id not in pet_data:
            pet_data[guild_id] = {
                "current_image": IMAGE_FILES["もちもち"],
                "personality": "まるまる",
                "feed_もちもち": 0,
                "feed_カチカチ": 0,
                "feed_キラキラ": 0,
                "feed_ふわふわ": 0,
                "last_image_change": "1970-01-01T00:00:00"
            }
            save_pet_data(pet_data)

        # 進化判定・更新
        check_and_update_evolution(pet_data, guild_id)

        data = pet_data[guild_id]

        embed = discord.Embed(title="🐾 ペットの状態", color=discord.Color.green())
        embed.add_field(name="性格", value=data.get("personality", "不明"), inline=False)

        image_file = data.get("current_image", IMAGE_FILES["もちもち"])
        image_path = os.path.join(PET_IMAGES_PATH, image_file)

        if os.path.exists(image_path):
            with open(image_path, "rb") as img:
                file = discord.File(img, filename=image_file)
                embed.set_image(url=f"attachment://{image_file}")
                await ctx.send(embed=embed, file=file)
        else:
            await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(PetCog(bot))
