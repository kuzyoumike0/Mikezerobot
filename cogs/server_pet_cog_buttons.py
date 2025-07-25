import discord
from discord.ext import commands, tasks
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

COOLDOWN_ACTIONS = {
    "キラキラ": "last_feed_",
    "カチカチ": "last_feed_",
    "もちもち": "last_feed_",
    "ふわふわ": "last_feed_",
    "散歩": "last_walk_",
    "撫でる": "last_pat_",
}

# 画像ファイル名を性格×機嫌で管理
MOODS = ["happy", "neutral", "angry"]
PERSONALITIES = ["もちもち", "カチカチ", "キラキラ", "ふわふわ"]
IMAGE_FILES = {
    personality: {mood: f"pet_{personality}_{mood}.png" for mood in MOODS}
    for personality in PERSONALITIES
}

def load_pet_data():
    if not os.path.exists(PET_DATA_PATH):
        return {}
    try:
        with open(PET_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] pets.json 読み込み失敗: {e}")
        return {}

def save_pet_data(data):
    os.makedirs(os.path.dirname(PET_DATA_PATH), exist_ok=True)
    with open(PET_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_mood_level(mood):
    if mood >= 70:
        return "happy"
    elif mood >= 40:
        return "neutral"
    else:
        return "angry"

def check_and_update_evolution(pet_data, guild_id):
    data = pet_data[guild_id]
    feed_counts = {k: data.get(f"feed_{k}", 0) for k in PERSONALITIES}
    total_feed = sum(feed_counts.values())
    now = datetime.datetime.utcnow()
    last_change = datetime.datetime.fromisoformat(data.get("last_image_change", "1970-01-01T00:00:00"))

    if (now - last_change).total_seconds() < 3600:
        return

    if total_feed >= EVOLVE_THRESHOLD:
        max_feed_type = max(feed_counts.items(), key=lambda x: (x[1], -EVOLVE_ORDER.index(x[0])))[0]
        data["personality"] = {
            "キラキラ": "キラキラ",
            "カチカチ": "カチカチ",
            "もちもち": "もちもち",
            "ふわふわ": "まるまる"
        }.get(max_feed_type, "まるまる")

        mood_level = get_mood_level(data.get("mood", 50))
        data["current_image"] = IMAGE_FILES[max_feed_type][mood_level]
        for k in PERSONALITIES:
            data[f"feed_{k}"] = max(0, data.get(f"feed_{k}", 0) - EVOLVE_THRESHOLD)
        data["last_image_change"] = now.isoformat()
        save_pet_data(pet_data)

class ActionButton(Button):
    def __init__(self, label, bot):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.bot = bot
        self.action = label

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        now = datetime.datetime.utcnow()
        pet_data = load_pet_data()

        if guild_id not in pet_data:
            await interaction.response.send_message("⚠️ ペットがまだ生成されていません。!pet で開始してください。", ephemeral=True)
            return

        if self.action in COOLDOWN_ACTIONS:
            cooldown_key = f"{COOLDOWN_ACTIONS[self.action]}{user_id}"
            last_time = datetime.datetime.fromisoformat(pet_data[guild_id].get(cooldown_key, "1970-01-01T00:00:00"))
            if (now - last_time).total_seconds() < 3600:
                await interaction.response.send_message(f"⏳ 「{self.action}」は1時間に1回だけ行えます。", ephemeral=True)
                return
            pet_data[guild_id][cooldown_key] = now.isoformat()

        pet_data[guild_id]["exp"] = pet_data[guild_id].get("exp", 0) + ACTION_EXP.get(self.action, 0)

        if self.action in PERSONALITIES:
            key = f"feed_{self.action}"
            pet_data[guild_id][key] = pet_data[guild_id].get(key, 0) + 1

        stats = pet_data[guild_id].setdefault("user_stats", {}).setdefault(user_id, {
            "feed_count": 0, "walk_count": 0, "pat_count": 0
        })

        if self.action in PERSONALITIES:
            stats["feed_count"] += 1
        elif self.action == "散歩":
            stats["walk_count"] += 1
        elif self.action == "撫でる":
            stats["pat_count"] += 1

        mood_boost = {
            "キラキラ": 5, "カチカチ": 5, "もちもち": 5, "ふわふわ": 5,
            "散歩": 10, "撫でる": 7
        }.get(self.action, 0)

        mood = min(100, pet_data[guild_id].get("mood", 50) + mood_boost)
        pet_data[guild_id]["mood"] = mood

        check_and_update_evolution(pet_data, guild_id)

        personality_key = {
            "まるまる": "ふわふわ",
            "キラキラ": "キラキラ",
            "カチカチ": "カチカチ",
            "もちもち": "もちもち"
        }.get(pet_data[guild_id].get("personality", "まるまる"), "ふわふわ")

        mood_level = get_mood_level(mood)
        pet_data[guild_id]["current_image"] = IMAGE_FILES[personality_key][mood_level]

        image_file = pet_data[guild_id]["current_image"]
        image_path = os.path.join(PET_IMAGES_PATH, image_file)
        save_pet_data(pet_data)

        embed = discord.Embed(title="🐶 ミルクシュガーの様子", color=discord.Color.green())
        embed.add_field(name="📈 経験値", value=f"{pet_data[guild_id]['exp']} XP", inline=False)
        embed.add_field(name="🏅 餌やり", value=f"{stats['feed_count']} 回", inline=True)
        embed.add_field(name="🚶 散歩", value=f"{stats['walk_count']} 回", inline=True)
        embed.add_field(name="🤗 撫でる", value=f"{stats['pat_count']} 回", inline=True)
        embed.add_field(name="🧠 機嫌", value=f"{mood} / 100", inline=False)
        embed.add_field(name="💖 性格", value=pet_data[guild_id]["personality"], inline=False)

        view = View()
        for action in ACTION_EXP.keys():
            view.add_item(ActionButton(action, self.bot))

        if os.path.exists(image_path):
            file = discord.File(image_path, filename=image_file)
            embed.set_image(url=f"attachment://{image_file}")
            await interaction.response.send_message(
                content=f"{interaction.user.mention} が「{self.action}」しました！",
                embed=embed, file=file, view=view
            )
        else:
            embed.description = "⚠️ 画像が見つかりません。"
            await interaction.response.send_message(embed=embed, view=view)

class PetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_image_loop.start()
        self.mood_decay_loop.start()

    @commands.command(name="pet")
    async def pet_command(self, ctx):
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        pet_data = load_pet_data()

        if guild_id not in pet_data:
            pet_data[guild_id] = {
                "exp": 0,
                "personality": "まるまる",
                "last_image_change": "1970-01-01T00:00:00",
                "user_stats": {},
                "mood": 50
            }
            for kind in PERSONALITIES:
                pet_data[guild_id][f"feed_{kind}"] = 0

        check_and_update_evolution(pet_data, guild_id)
        mood = pet_data[guild_id]["mood"]
        mood_level = get_mood_level(mood)
        personality_key = {
            "まるまる": "ふわふわ",
            "キラキラ": "キラキラ",
            "カチカチ": "カチカチ",
            "もちもち": "もちもち"
        }.get(pet_data[guild_id]["personality"], "ふわふわ")
        image_file = IMAGE_FILES[personality_key][mood_level]
        pet_data[guild_id]["current_image"] = image_file
        save_pet_data(pet_data)

        stats = pet_data[guild_id].get("user_stats", {}).get(user_id, {
            "feed_count": 0, "walk_count": 0, "pat_count": 0
        })

        embed = discord.Embed(title="🐶 ミルクシュガーの様子", color=discord.Color.green())
        embed.add_field(name="📈 経験値", value=f"{pet_data[guild_id]['exp']} XP", inline=False)
        embed.add_field(name="🏅 餌やり", value=f"{stats['feed_count']} 回", inline=True)
        embed.add_field(name="🚶 散歩", value=f"{stats['walk_count']} 回", inline=True)
        embed.add_field(name="🤗 撫でる", value=f"{stats['pat_count']} 回", inline=True)
        embed.add_field(name="🧠 機嫌", value=f"{mood} / 100", inline=False)
        embed.add_field(name="💖 性格", value=pet_data[guild_id]["personality"], inline=False)

        view = View()
        for action in ACTION_EXP.keys():
            view.add_item(ActionButton(action, self.bot))

        image_path = os.path.join(PET_IMAGES_PATH, image_file)
        if os.path.exists(image_path):
            file = discord.File(image_path, filename=image_file)
            embed.set_image(url=f"attachment://{image_file}")
            await ctx.send(embed=embed, file=file, view=view)
        else:
            embed.description = "⚠️ ペット画像が見つかりません。"
            await ctx.send(embed=embed, view=view)

    @commands.command(name="pet_ranking")
    async def pet_ranking_command(self, ctx):
        guild_id = str(ctx.guild.id)
        pet_data = load_pet_data()
        if guild_id not in pet_data or "user_stats" not in pet_data[guild_id]:
            await ctx.send("⚠️ ランキングデータがありません。")
            return

        rankings = sorted(
            pet_data[guild_id]["user_stats"].items(),
            key=lambda x: x[1].get("feed_count", 0),
            reverse=True
        )
        embed = discord.Embed(title="🥇 餌やりランキング", color=discord.Color.gold())
        for i, (uid, stats) in enumerate(rankings[:10], start=1):
            member = ctx.guild.get_member(int(uid))
            name = member.display_name if member else f"ID:{uid}"
            embed.add_field(name=f"{i}位: {name}", value=f"{stats.get('feed_count',0)} 回", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="pet_help")
    async def pet_help_command(self, ctx):
        embed = discord.Embed(title="📘 ペットコマンドヘルプ", description=(
            "!pet - ペットの状態を表示します。\n"
            "!pet_ranking - 餌やりランキングを表示します。\n"
            "!pet_help - このヘルプを表示します。"
        ), color=discord.Color.blue())
        await ctx.send(embed=embed)

    @tasks.loop(minutes=180)
    async def update_image_loop(self):
        pass  # Reserved if needed for future batch updates

    @tasks.loop(minutes=120)
    async def mood_decay_loop(self):
        pet_data = load_pet_data()
        updated = False
        for guild_id, data in pet_data.items():
            mood = data.get("mood", 50)
            new_mood = max(0, mood - 10)
            if new_mood != mood:
                data["mood"] = new_mood
                updated = True
        if updated:
            save_pet_data(pet_data)

    @update_image_loop.before_loop
    async def before_update_image_loop(self):
        await self.bot.wait_until_ready()

    @mood_decay_loop.before_loop
    async def before_mood_decay_loop(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.update_image_loop.cancel()
        self.mood_decay_loop.cancel()

async def setup(bot):
    await bot.add_cog(PetCog(bot))
