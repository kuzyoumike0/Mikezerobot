import discord
from discord.ext import commands
from discord.ui import View, button
import os
import json
from datetime import datetime

PET_DATA_PATH = "data/pets.json"
PET_IMAGES_PATH = "images"

FOOD_VALUES = {
    "キラキラ": 10,
    "カチカチ": 10,
    "もちもち": 10,
    "ふわふわ": 10
}

# 初期性格
INITIAL_PERSONALITY = "まるまる"

def load_pet_data():
    if os.path.exists(PET_DATA_PATH):
        with open(PET_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_pet_data(data):
    os.makedirs(os.path.dirname(PET_DATA_PATH), exist_ok=True)
    with open(PET_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_image_path(personality, mood):
    base_personality = personality
    if personality == "まるまる":
        base_personality = "neutral"  # 仮に neutral を割り当てても存在しない可能性があるので注意
    filename = f"pet_{base_personality}_{mood}.png"
    return os.path.join(PET_IMAGES_PATH, filename)

class PetActionView(View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = str(guild_id)

    @button(label="撫でる", style=discord.ButtonStyle.primary, custom_id="pet_nade")
    async def nade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_action(interaction, "撫でる")

    @button(label="散歩", style=discord.ButtonStyle.success, custom_id="pet_walk")
    async def walk_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_action(interaction, "散歩")

    @button(label="キラキラ", style=discord.ButtonStyle.secondary, custom_id="pet_feed_kirakira")
    async def feed_kirakira_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_action(interaction, "キラキラ")

    @button(label="カチカチ", style=discord.ButtonStyle.secondary, custom_id="pet_feed_kachikachi")
    async def feed_kachikachi_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_action(interaction, "カチカチ")

    @button(label="もちもち", style=discord.ButtonStyle.secondary, custom_id="pet_feed_mochimochi")
    async def feed_mochimochi_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_action(interaction, "もちもち")

    @button(label="ふわふわ", style=discord.ButtonStyle.secondary, custom_id="pet_feed_fuwafuwa")
    async def feed_fuwafuwa_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_action(interaction, "ふわふわ")

    async def handle_action(self, interaction: discord.Interaction, action: str):
        pet_data = load_pet_data()
        guild_data = pet_data.get(self.guild_id, {
            "exp": 0,
            "personality": INITIAL_PERSONALITY,
            "mood": "neutral"
        })

        if action in FOOD_VALUES:
            guild_data["exp"] += FOOD_VALUES[action]
            # 性格を餌に応じて変化（最後に与えた餌のタイプ）
            guild_data["personality"] = action
            guild_data["mood"] = "happy"
        elif action == "撫でる":
            guild_data["mood"] = "happy"
        elif action == "散歩":
            guild_data["mood"] = "neutral"

        pet_data[self.guild_id] = guild_data
        save_pet_data(pet_data)

        embed = discord.Embed(
            title="あなたのペット",
            description=f"性格: {guild_data['personality']}\n機嫌: {guild_data['mood']}\n経験値: {guild_data['exp']}",
            color=discord.Color.green()
        )

        image_path = get_image_path(guild_data["personality"], guild_data["mood"])
        if os.path.exists(image_path):
            file = discord.File(image_path, filename="pet.png")
            embed.set_image(url="attachment://pet.png")
            await interaction.response.send_message(embed=embed, file=file, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

class PetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pet")
    async def pet_command(self, ctx):
        """ペットの状態を表示"""
        pet_data = load_pet_data()
        guild_id = str(ctx.guild.id)
        guild_data = pet_data.get(guild_id, {
            "exp": 0,
            "personality": INITIAL_PERSONALITY,
            "mood": "neutral"
        })

        embed = discord.Embed(
            title="あなたのペット",
            description=f"性格: {guild_data['personality']}\n機嫌: {guild_data['mood']}\n経験値: {guild_data['exp']}",
            color=discord.Color.green()
        )

        image_path = get_image_path(guild_data["personality"], guild_data["mood"])
        view = PetActionView(self.bot, ctx.guild.id)

        if os.path.exists(image_path):
            file = discord.File(image_path, filename="pet.png")
            embed.set_image(url="attachment://pet.png")
            await ctx.send(embed=embed, file=file, view=view)
        else:
            await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(PetCog(bot))
