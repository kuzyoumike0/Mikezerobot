import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
import datetime

PET_DATA_PATH = "data/pets.json"
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

def get_pet_image_path(personality: str, mood_score: int) -> str:
    # moodスコアにより画像の表情を選択
    if mood_score >= 70:
        mood = "happy"
    elif mood_score >= 40:
        mood = "neutral"
    else:
        mood = "angry"

    personality_map = {
        "ふわふわ": "fuwafuwa",
        "キラキラ": "kirakira",
        "カチカチ": "kachikachi",
        "もちもち": "mochimochi",
    }

    p = personality_map.get(personality, "fuwafuwa")
    filename = f"images/pet_{p}_{mood}.png"
    return filename

class PetButtonView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = str(user_id)

        # 餌ボタンを追加
        for food in FOOD_VALUES:
            self.add_item(PetActionButton(label=food, action="feed", style=discord.ButtonStyle.primary, user_id=self.user_id, bot=bot))

        # 散歩ボタン
        self.add_item(PetActionButton(label="散歩", action="walk", style=discord.ButtonStyle.success, user_id=self.user_id, bot=bot))
        # 撫でるボタン
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

        # 利用履歴ロード
        timestamps = load_json(TIMESTAMP_PATH)
        user_times = timestamps.get(user_id, {})
        last_time_str = user_times.get(self.action)

        if last_time_str:
            last_time = datetime.datetime.fromisoformat(last_time_str)
            if now - last_time < datetime.timedelta(hours=1):
                await interaction.response.send_message(f"{self.label}は1時間に1回だけ使えます。", ephemeral=True)
                return

        # タイムスタンプ更新
        user_times[self.action] = now.isoformat()
        timestamps[user_id] = user_times
        save_json(TIMESTAMP_PATH, timestamps)

        # ペットデータ読み込み
        pet = load_json(PET_DATA_PATH, default={
            "personality": "ふわふわ",
            "mood": 50,
            "exp": {"キラキラ":0, "カチカチ":0, "もちもち":0, "ふわふわ":0, "walk":0, "pet":0}
        })

        # アクション別処理
        if self.action == "feed":
            category = self.label
            pet["exp"][category] = pet["exp"].get(category, 0) + 1
            pet["mood"] = min(100, pet.get("mood", 50) + 3)
            pet["personality"] = category
            await interaction.response.send_message(f"🍚 {category}をあげました！", ephemeral=True)

        elif self.action == "walk":
            pet["mood"] = max(0, pet.get("mood", 50) - 5)
            pet["exp"]["walk"] = pet["exp"].get("walk", 0) + 1
            await interaction.response.send_message("テクテク……いい天気だったね！☀️", ephemeral=True)

        elif self.action == "pet":
            pet["mood"] = min(100, pet.get("mood", 50) + 5)
            pet["exp"]["pet"] = pet["exp"].get("pet", 0) + 1
            await interaction.response.send_message("なでなで……ミルクシュガーは嬉しそう！✨", ephemeral=True)

        # ペットデータ保存
        save_json(PET_DATA_PATH, pet)

class ペットゲーム(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pet")
    async def show_pet(self, ctx):
        pet = load_json(PET_DATA_PATH, default={
            "personality": "ふわふわ",
            "mood": 50,
            "exp": {"キラキラ":0, "カチカチ":0, "もちもち":0, "ふわふわ":0, "walk":0, "pet":0}
        })

        personality = pet.get("personality", "ふわふわ")
        mood = pet.get("mood", 50)

        image_path = get_pet_image_path(personality, mood)

        # 画像ファイルが存在しない場合の代替
        if not os.path.exists(image_path):
            image_path = "images/pet_fuwafuwa_neutral.png"

        file = discord.File(image_path, filename="pet.png")

        embed = discord.Embed(
            title="🐶 ミルクシュガーの育成",
            description=f"性格: {personality}\n機嫌: {mood}/100",
            color=discord.Color.pink()
        )
        embed.set_image(url="attachment://pet.png")

        view = PetButtonView(bot=self.bot, user_id=ctx.author.id)
        await ctx.send(embed=embed, file=file, view=view)

async def setup(bot):
    await bot.add_cog(ペットゲーム(bot))
