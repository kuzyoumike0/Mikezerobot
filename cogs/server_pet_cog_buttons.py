import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
import datetime

PET_DATA_PATH = "data/pets.json"
PET_IMAGES_PATH = "images"

ACTION_EXP = {
    "キラキラ": 10,
    "カチカチ": 10,
    "もちもち": 10,
    "ふわふわ": 10,
    "散歩": 5,
    "撫でる": 7,
}

EVOLVE_THRESHOLD = 100
EVOLVE_ORDER = ["もちもち", "カチカチ", "キラキラ", "ふわふわ"]

IMAGE_FILES = {
    "もちもち": "pet_mochimochi.png",
    "カチカチ": "pet_kachikachi.png",
    "キラキラ": "pet_kirakira.png",
    "ふわふわ": "pet_fuwafuwa.png",
}

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
        max_feed_type = max(EVOLVE_ORDER, key=lambda k: feed_counts[k])
        data["current_image"] = IMAGE_FILES[max_feed_type]
        for kind in IMAGE_FILES.keys():
            data[f"feed_{kind}"] = max(0, data.get(f"feed_{kind}", 0) - EVOLVE_THRESHOLD)
        data["last_image_change"] = now.isoformat()
        data["personality"] = {
            "キラキラ": "キラキラ",
            "カチカチ": "カチカチ",
            "もちもち": "もちもち",
            "ふわふわ": "まるまる"
        }.get(max_feed_type, "普通")
        save_pet_data(pet_data)

class FeedButton(Button):
    def __init__(self, label, pet_cog):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.label = label
        self.pet_cog = pet_cog

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        pet_data = load_pet_data()

        if guild_id not in pet_data:
            pet_data[guild_id] = {
                "exp": 0,
                "personality": "まるまる",
                "current_image": "pet_mochimochi.png",
                "last_image_change": datetime.datetime.utcnow().isoformat(),
            }

        pet = pet_data[guild_id]
        pet["exp"] = pet.get("exp", 0) + ACTION_EXP[self.label]
        pet[f"feed_{self.label}"] = pet.get(f"feed_{self.label}", 0) + 1

        check_and_update_evolution(pet_data, guild_id)
        save_pet_data(pet_data)

        await interaction.response.send_message(f"{self.label} を与えました！", ephemeral=True)
        await self.pet_cog.send_pet_status(interaction.channel)

class PetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pet")
    async def pet_status(self, ctx):
        await self.send_pet_status(ctx.channel)

    async def send_pet_status(self, channel):
        guild_id = str(channel.guild.id)
        pet_data = load_pet_data()

        if guild_id not in pet_data:
            pet_data[guild_id] = {
                "exp": 0,
                "personality": "まるまる",
                "current_image": "pet_mochimochi.png",
                "last_image_change": datetime.datetime.utcnow().isoformat(),
            }
            save_pet_data(pet_data)

        pet = pet_data[guild_id]

        embed = discord.Embed(title="🐾 サーバーペット", description=f"性格：**{pet.get('personality', 'まるまる')}**\n経験値：{pet.get('exp', 0)}", color=0x00bfff)
        image_path = os.path.join(PET_IMAGES_PATH, pet["current_image"])
        if os.path.exists(image_path):
            file = discord.File(image_path, filename="pet.png")
            embed.set_image(url="attachment://pet.png")
            view = View()
            for label in ACTION_EXP.keys():
                view.add_item(FeedButton(label, self))
            await channel.send(embed=embed, view=view, file=file)
        else:
            await channel.send("ペット画像が見つかりません。")

async def setup(bot):
    await bot.add_cog(PetCog(bot))
