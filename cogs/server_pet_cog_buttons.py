import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import json
import os
import datetime

PET_DATA_PATH = "data/pets.json"
PET_IMAGES_PATH = "images"
MOOD_DECREASE_INTERVAL = 2  # 時間
MOOD_DECREASE_AMOUNT = 15
EXPERIENCE_THRESHOLD = 100
ACTION_COOLDOWN = datetime.timedelta(hours=1)
FOOD_VALUES = {
    "キラキラ": 10,
    "カチカチ": 10,
    "もちもち": 10,
    "ふわふわ": 10
}

class PetView(View):
    def __init__(self, bot, data, user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.data = data
        self.user_id = str(user_id)

        for food in FOOD_VALUES:
            self.add_item(FeedButton(bot, food, label=food, style=discord.ButtonStyle.primary))
        self.add_item(WalkButton(bot))
        self.add_item(PetButton(bot))

class FeedButton(Button):
    def __init__(self, bot, food, **kwargs):
        super().__init__(**kwargs)
        self.bot = bot
        self.food = food

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        data = load_pet_data()

        if not is_action_allowed(user_id, self.food, data["last_actions"]):
            await interaction.response.send_message("その餌はまだあげられません（1時間に1回まで）", ephemeral=True)
            return

        data["experience"][self.food] += FOOD_VALUES[self.food]
        update_last_action(user_id, self.food, data["last_actions"])
        check_evolution(data)
        save_pet_data(data)

        await interaction.response.edit_message(embed=create_pet_embed(data), view=PetView(self.bot, data, user_id))

class WalkButton(Button):
    def __init__(self, bot):
        super().__init__(label="散歩", style=discord.ButtonStyle.success)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        data = load_pet_data()

        if not is_action_allowed(user_id, "散歩", data["last_actions"]):
            await interaction.response.send_message("散歩は1時間に1回までです。", ephemeral=True)
            return

        data["mood"] = min(100, data["mood"] + 10)
        update_last_action(user_id, "散歩", data["last_actions"])
        save_pet_data(data)

        await interaction.response.edit_message(embed=create_pet_embed(data), view=PetView(self.bot, data, user_id))

class PetButton(Button):
    def __init__(self, bot):
        super().__init__(label="撫でる", style=discord.ButtonStyle.secondary)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        data = load_pet_data()

        if not is_action_allowed(user_id, "撫でる", data["last_actions"]):
            await interaction.response.send_message("撫でるのは1時間に1回までです。", ephemeral=True)
            return

        data["mood"] = min(100, data["mood"] + 5)
        update_last_action(user_id, "撫でる", data["last_actions"])
        save_pet_data(data)

        await interaction.response.edit_message(embed=create_pet_embed(data), view=PetView(self.bot, data, user_id))

def load_pet_data():
    if not os.path.exists(PET_DATA_PATH):
        return {
            "name": "ミルクシュガー",
            "mood": 100,
            "personality": "まるまる",
            "experience": {food: 0 for food in FOOD_VALUES},
            "last_actions": {},
            "evolution_stage": 0
        }
    with open(PET_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_pet_data(data):
    with open(PET_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_action_allowed(user_id, action, last_actions):
    user_actions = last_actions.get(user_id, {})
    last_time_str = user_actions.get(action)
    if last_time_str:
        last_time = datetime.datetime.fromisoformat(last_time_str)
        if datetime.datetime.now() - last_time < ACTION_COOLDOWN:
            return False
    return True

def update_last_action(user_id, action, last_actions):
    if user_id not in last_actions:
        last_actions[user_id] = {}
    last_actions[user_id][action] = datetime.datetime.now().isoformat()

def check_evolution(data):
    for food, value in data["experience"].items():
        if value >= EXPERIENCE_THRESHOLD:
            data["personality"] = food
            data["evolution_stage"] += 1
            for k in data["experience"]:
                data["experience"][k] = 0
            break

def create_pet_embed(data):
    embed = discord.Embed(title=f"{data['name']}のようす",
                          description=f"性格: {data['personality']}\n機嫌: {data['mood']}/100",
                          color=discord.Color.pink())
    image_filename = f"pet_{data['personality']}_angry.png" if data['mood'] < 30 else f"pet_{data['personality']}_normal.png"
    image_path = os.path.join(PET_IMAGES_PATH, image_filename)
    if os.path.exists(image_path):
        file = discord.File(image_path, filename="pet.png")
        embed.set_image(url="attachment://pet.png")
        return embed, file
    return embed, None

class ServerPetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mood_task.start()

    @commands.command(name="pet")
    async def pet_command(self, ctx):
        data = load_pet_data()
        embed, file = create_pet_embed(data)
        view = PetView(self.bot, data, ctx.author.id)
        if file:
            await ctx.send(embed=embed, view=view, file=file)
        else:
            await ctx.send(embed=embed, view=view)

    @tasks.loop(hours=MOOD_DECREASE_INTERVAL)
    async def mood_task(self):
        data = load_pet_data()
        data["mood"] = max(0, data["mood"] - MOOD_DECREASE_AMOUNT)
        save_pet_data(data)

    @mood_task.before_loop
    async def before_mood_task(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(ServerPetCog(bot))
