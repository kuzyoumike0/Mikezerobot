import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import json
import os
import datetime

# 設定ファイルパス
PET_DATA_PATH = "data/pets.json"
PET_IMAGES_PATH = "images"

# 餌の種類と経験値
FOOD_VALUES = {
    "キラキラ": ("kirakira", 10),
    "カチカチ": ("kachikachi", 10),
    "もちもち": ("mochimochi", 10),
    "ふわふわ": ("fuwafuwa", 10)
}

# 各操作のクールダウン（秒）
COOLDOWN = 3600
MOOD_DECREASE_INTERVAL = 7200
MOOD_DECREASE_AMOUNT = 15

# 初期化
if not os.path.exists("data"):
    os.makedirs("data")
if not os.path.exists(PET_DATA_PATH):
    with open(PET_DATA_PATH, "w") as f:
        json.dump({"personality": "まるまる", "mood": 100, "experience": {}, "last_actions": {}, "evolved": False}, f)

# データ読み書き関数
def load_pet():
    with open(PET_DATA_PATH, "r") as f:
        return json.load(f)

def save_pet(data):
    with open(PET_DATA_PATH, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 性格別画像取得
def get_image(personality, mood):
    mood_type = "happy" if mood >= 70 else "neutral" if mood >= 30 else "angry"
    if personality == "まるまる":
        filename = f"pet_marumaru_{mood_type}.png"
    else:
        filename = f"pet_{personality}_{mood_type}.png"
    return os.path.join(PET_IMAGES_PATH, filename)

# ペット表示用ビュー
class PetView(View):
    def __init__(self, bot, user):
        super().__init__(timeout=None)
        self.bot = bot
        self.user = user
        for label in FOOD_VALUES.keys():
            self.add_item(FeedButton(label, self.user))
        self.add_item(WalkButton(self.user))
        self.add_item(PatButton(self.user))

class FeedButton(Button):
    def __init__(self, label, user):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.user = user

    async def callback(self, interaction):
        if interaction.user != self.user:
            return await interaction.response.send_message("これはあなたの操作ではありません。", ephemeral=True)

        data = load_pet()
        now = datetime.datetime.utcnow().timestamp()
        action_key = f"{interaction.user.id}_feed"
        last_time = data["last_actions"].get(action_key, 0)

        if now - last_time < COOLDOWN:
            return await interaction.response.send_message("餌は1時間に1回までです。", ephemeral=True)

        food_key, exp = FOOD_VALUES[self.label]
        data["experience"][food_key] = data["experience"].get(food_key, 0) + exp
        data["last_actions"][action_key] = now

        # 進化処理
        if data["experience"][food_key] >= 100:
            data["personality"] = food_key
            data["experience"][food_key] = 0
            data["evolved"] = True

        save_pet(data)
        await interaction.response.send_message(f"{self.label}をあげました！", ephemeral=True)

class WalkButton(Button):
    def __init__(self, user):
        super().__init__(label="散歩", style=discord.ButtonStyle.success)
        self.user = user

    async def callback(self, interaction):
        if interaction.user != self.user:
            return await interaction.response.send_message("これはあなたの操作ではありません。", ephemeral=True)

        data = load_pet()
        now = datetime.datetime.utcnow().timestamp()
        action_key = f"{interaction.user.id}_walk"
        last_time = data["last_actions"].get(action_key, 0)

        if now - last_time < COOLDOWN:
            return await interaction.response.send_message("散歩は1時間に1回までです。", ephemeral=True)

        data["mood"] = min(100, data["mood"] + 10)
        data["last_actions"][action_key] = now
        save_pet(data)
        await interaction.response.send_message("散歩しました！", ephemeral=True)

class PatButton(Button):
    def __init__(self, user):
        super().__init__(label="撫でる", style=discord.ButtonStyle.secondary)
        self.user = user

    async def callback(self, interaction):
        if interaction.user != self.user:
            return await interaction.response.send_message("これはあなたの操作ではありません。", ephemeral=True)

        data = load_pet()
        now = datetime.datetime.utcnow().timestamp()
        action_key = f"{interaction.user.id}_pat"
        last_time = data["last_actions"].get(action_key, 0)

        if now - last_time < COOLDOWN:
            return await interaction.response.send_message("撫でるのは1時間に1回までです。", ephemeral=True)

        data["mood"] = min(100, data["mood"] + 5)
        data["last_actions"][action_key] = now
        save_pet(data)
        await interaction.response.send_message("撫でました！", ephemeral=True)

class PetBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mood_task.start()

    def cog_unload(self):
        self.mood_task.cancel()

    @commands.command(name="pet")
    async def show_pet(self, ctx):
        data = load_pet()
        file_path = get_image(data["personality"], data["mood"])
        file = discord.File(file_path, filename="pet.png")

        embed = discord.Embed(title="✨ ミルクシュガーの状態 ✨")
        embed.set_image(url="attachment://pet.png")
        embed.add_field(name="性格", value=data["personality"], inline=True)
        embed.add_field(name="機嫌", value=str(data["mood"]), inline=True)
        embed.add_field(name="経験値", value=str(data["experience"]), inline=False)

        await ctx.send(embed=embed, file=file, view=PetView(self.bot, ctx.author))

    @tasks.loop(seconds=MOOD_DECREASE_INTERVAL)
    async def mood_task(self):
        data = load_pet()
        data["mood"] = max(0, data["mood"] - MOOD_DECREASE_AMOUNT)
        save_pet(data)

async def setup(bot):
    await bot.add_cog(PetBot(bot))
