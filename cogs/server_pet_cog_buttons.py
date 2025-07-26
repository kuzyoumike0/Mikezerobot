import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import json
import os
import datetime

# データパス
PET_DATA_PATH = "data/pets.json"
PET_IMAGES_PATH = "images"
TIMESTAMP_PATH = "data/interaction_timestamps.json"

# 餌の種類と性格
FOOD_VALUES = {
    "キラキラ": ("kirakira", 10),
    "カチカチ": ("kachikachi", 10),
    "もちもち": ("mochimochi", 10),
    "ふわふわ": ("fuwafuwa", 10),
}

def load_json(path, default={}):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_pet_image(personality: str, mood: str) -> str:
    filename = f"pet_{personality}_{mood}.png"
    return os.path.join(PET_IMAGES_PATH, filename)

def get_pet_data():
    return load_json(PET_DATA_PATH, default={
        "personality": "marumaru",
        "mood": 100,
        "experience": {
            "kirakira": 0,
            "kachikachi": 0,
            "mochimochi": 0,
            "fuwafuwa": 0
        }
    })

def save_pet_data(data):
    save_json(PET_DATA_PATH, data)

def get_mood_status(mood: int) -> str:
    return "happy" if mood >= 50 else "angry"

class PetButtonView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = str(user_id)

        for food in FOOD_VALUES:
            self.add_item(PetActionButton(label=food, action="feed", style=discord.ButtonStyle.primary, user_id=self.user_id, bot=bot))

        self.add_item(PetActionButton(label="散歩", action="walk", style=discord.ButtonStyle.success, user_id=self.user_id, bot=bot))
        self.add_item(PetActionButton(label="撫でる", action="pet", style=discord.ButtonStyle.secondary, user_id=self.user_id, bot=bot))

class PetActionButton(Button):
    def __init__(self, label, action, style, user_id, bot):
        super().__init__(label=label, style=style)
        self.label = label
        self.action = action
        self.user_id = user_id
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        now = datetime.datetime.now()

        timestamps = load_json(TIMESTAMP_PATH)
        user_times = timestamps.get(user_id, {})
        last_time_str = user_times.get(self.action)
        if last_time_str:
            last_time = datetime.datetime.fromisoformat(last_time_str)
            if now - last_time < datetime.timedelta(hours=1):
                await interaction.response.send_message(f"{self.label}は1時間に1回だけ使えます。", ephemeral=True)
                return

        user_times[self.action] = now.isoformat()
        timestamps[user_id] = user_times
        save_json(TIMESTAMP_PATH, timestamps)

        await interaction.response.send_message(f"{self.label} を実行しました！", ephemeral=True)

        if self.action == "feed":
            await self.handle_feed(interaction)
        elif self.action == "walk":
            await self.handle_walk(interaction)
        elif self.action == "pet":
            await self.handle_pet(interaction)

    async def handle_feed(self, interaction):
        pet_data = get_pet_data()
        key, exp = FOOD_VALUES[self.label]
        pet_data["experience"][key] += exp

        if pet_data["experience"][key] >= 100:
            pet_data["personality"] = key
            for k in pet_data["experience"]:
                pet_data["experience"][k] = 0

        save_pet_data(pet_data)

    async def handle_walk(self, interaction):
        pet_data = get_pet_data()
        pet_data["mood"] = min(pet_data["mood"] + 10, 100)
        save_pet_data(pet_data)

    async def handle_pet(self, interaction):
        pet_data = get_pet_data()
        pet_data["mood"] = min(pet_data["mood"] + 5, 100)
        save_pet_data(pet_data)

class ペットゲーム(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pet")
    async def show_pet(self, ctx):
        pet_data = get_pet_data()
        personality = pet_data.get("personality", "marumaru")
        mood_value = pet_data.get("mood", 100)
        mood_status = get_mood_status(mood_value)

        image_path = get_pet_image(personality, mood_status)
        file = discord.File(image_path, filename="pet.png")

        embed = discord.Embed(
            title="🐾 ミルクシュガーのお世話 🐾",
            description=f"性格: **{personality}**\n機嫌: **{mood_value}** ({'良い' if mood_status == 'happy' else '悪い'})",
            color=discord.Color.pink()
        )
        embed.set_image(url="attachment://pet.png")

        view = PetButtonView(bot=self.bot, user_id=ctx.author.id)
        await ctx.send(embed=embed, file=file, view=view)

async def setup(bot):
    await bot.add_cog(ペットゲーム(bot))
