import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import json
import os
import datetime

PET_DATA_PATH = "data/pets.json"
PET_IMAGES_PATH = "images"
TIMESTAMP_PATH = "data/interaction_timestamps.json"

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

        # 更新
        user_times[self.action] = now.isoformat()
        timestamps[user_id] = user_times
        save_json(TIMESTAMP_PATH, timestamps)

        await interaction.response.send_message(f"{self.label} を実行しました！", ephemeral=True)

        # 各アクションに応じた処理を入れる（以下は簡易例）
        if self.action == "feed":
            await self.handle_feed(interaction)
        elif self.action == "walk":
            await self.handle_walk(interaction)
        elif self.action == "pet":
            await self.handle_pet(interaction)

    async def handle_feed(self, interaction):
        # ここに餌やり処理を記述（省略可能）
        pass

    async def handle_walk(self, interaction):
        # ここに散歩処理を記述（省略可能）
        pass

    async def handle_pet(self, interaction):
        # ここに撫でる処理を記述（省略可能）
        pass

class ペットゲーム(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pet")
    async def show_pet(self, ctx):
        view = PetButtonView(bot=self.bot, user_id=ctx.author.id)
        await ctx.send("ミルクシュガーのお世話メニューです", view=view)

async def setup(bot):
    await bot.add_cog(ペットゲーム(bot))
