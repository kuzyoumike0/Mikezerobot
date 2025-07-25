import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import os
import random

PET_DATA_PATH = "data/pets.json"
PET_IMAGES_PATH = "images"

# 餌と性格の対応
FOOD_VALUES = {
    "キラキラ": "kirakira",
    "カチカチ": "kachikachi",
    "もちもち": "mochimochi",
    "ふわふわ": "fuwafuwa"
}

MOODS = ["happy", "neutral", "angry"]

# 初期状態の性格
INITIAL_PERSONALITY = "fuwafuwa"

def load_pet_data():
    if not os.path.exists(PET_DATA_PATH):
        return {}
    with open(PET_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_pet_data(data):
    with open(PET_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def determine_personality(feed_counts):
    if sum(feed_counts.values()) < 100:
        return None  # 進化しない
    return max(feed_counts, key=feed_counts.get)

def get_mood():
    return random.choice(MOODS)

class FeedView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id

        for food in FOOD_VALUES.keys():
            self.add_item(self.create_food_button(food))

    def create_food_button(self, food_type):
        label = food_type
        custom_id = f"feed_{food_type}_{self.user_id}"

        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("これはあなたのペットではありません。", ephemeral=True)
                return

            pet_data = load_pet_data()
            user_id = str(interaction.user.id)
            if user_id not in pet_data:
                pet_data[user_id] = {
                    "personality": INITIAL_PERSONALITY,
                    "feed_counts": {key: 0 for key in FOOD_VALUES.values()}
                }

            personality = pet_data[user_id]["personality"]
            feed_counts = pet_data[user_id]["feed_counts"]

            personality_key = FOOD_VALUES[food_type]
            feed_counts[personality_key] += 10

            if sum(feed_counts.values()) >= 100:
                new_personality = determine_personality(feed_counts)
                if new_personality:
                    pet_data[user_id]["personality"] = new_personality
                    pet_data[user_id]["feed_counts"] = {key: 0 for key in FOOD_VALUES.values()}
                    personality = new_personality

            save_pet_data(pet_data)

            mood = get_mood()
            image_file = f"pet_{personality}_{mood}.png"
            image_path = os.path.join(PET_IMAGES_PATH, image_file)

            embed = discord.Embed(title="あなたのペットの様子", description=f"性格: {personality}\n機嫌: {mood}", color=0xabcdef)
            file = discord.File(image_path, filename=image_file)
            embed.set_image(url=f"attachment://{image_file}")

            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

        return Button(label=label, style=discord.ButtonStyle.primary, custom_id=custom_id, row=0, callback=callback)

class ServerPetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pet")
    async def show_pet(self, ctx):
        user_id = str(ctx.author.id)
        pet_data = load_pet_data()

        if user_id not in pet_data:
            pet_data[user_id] = {
                "personality": INITIAL_PERSONALITY,
                "feed_counts": {key: 0 for key in FOOD_VALUES.values()}
            }
            save_pet_data(pet_data)

        personality = pet_data[user_id]["personality"]
        mood = get_mood()
        image_file = f"pet_{personality}_{mood}.png"
        image_path = os.path.join(PET_IMAGES_PATH, image_file)

        embed = discord.Embed(title="あなたのペット", description=f"性格: {personality}\n機嫌: {mood}", color=0xabcdef)
        file = discord.File(image_path, filename=image_file)
        embed.set_image(url=f"attachment://{image_file}")

        view = FeedView(self.bot, ctx.author.id)
        await ctx.send(embed=embed, file=file, view=view)

async def setup(bot):
    await bot.add_cog(ServerPetCog(bot))
