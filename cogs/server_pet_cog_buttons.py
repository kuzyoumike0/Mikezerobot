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
    with open(PET_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "personality": "fuwafuwa",
            "mood": 100,
            "experience": {},
            "last_actions": {},
            "evolved": False
        }, f, ensure_ascii=False, indent=4)

# データ読み書き関数
def load_pet():
    with open(PET_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_pet(data):
    with open(PET_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 性格と機嫌から画像取得（機嫌は3段階で判定）
def get_image(personality, mood):
    if mood <= 30:
        mood_type = "angry"
    elif mood <= 60:
        mood_type = "neutral"
    else:
        mood_type = "happy"
    filename = f"pet_{personality}_{mood_type}.png"
    path = os.path.join(PET_IMAGES_PATH, filename)
    if not os.path.exists(path):
        path = os.path.join(PET_IMAGES_PATH, "pet_fuwafuwa_neutral.png")  # 予備画像
    return path

# ビュー定義
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

        data["mood"] = min(100, data.get("mood", 100) + 10)
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

        data["mood"] = min(100, data.get("mood", 100) + 5)
        data["last_actions"][action_key] = now
        save_pet(data)
        await interaction.response.send_message("撫でました！", ephemeral=True)

# コグ定義
class PetBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mood_task.start()

    def cog_unload(self):
        self.mood_task.cancel()

    @commands.command(name="pet")
    async def show_pet(self, ctx):
        data = load_pet()
        file_path = get_image(data.get("personality", "fuwafuwa"), data.get("mood", 100))
        file = discord.File(file_path, filename="pet.png")

        embed = discord.Embed(title="✨ ミルクシュガーの状態 ✨", color=0xffc0cb)
        embed.set_image(url="attachment://pet.png")
        embed.add_field(name="性格", value=data.get("personality", "ふわふわ"), inline=True)
        embed.add_field(name="機嫌", value=f"{data.get('mood', 100)}/100", inline=True)
        exp_display = "\n".join([f"{k}: {v}" for k, v in data.get("experience", {}).items()])
        embed.add_field(name="経験値", value=exp_display or "なし", inline=False)

        await ctx.send(embed=embed, file=file, view=PetView(self.bot, ctx.author))

    @tasks.loop(seconds=MOOD_DECREASE_INTERVAL)
    async def mood_task(self):
        data = load_pet()
        # moodキーがなければ100で初期化
        mood = data.get("mood", 100)
        data["mood"] = max(0, mood - MOOD_DECREASE_AMOUNT)
        save_pet(data)

    @mood_task.before_loop
    async def before_mood_task(self):
        await self.bot.wait_until_ready()

# 起動時に呼ばれる関数
async def setup(bot):
    await bot.add_cog(PetBot(bot))
