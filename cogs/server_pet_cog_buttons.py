import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
from datetime import datetime, timedelta

from config import FEED_TITLE_ROLES

PET_DATA_PATH = "data/pets.json"

FOOD_VALUES = {
    "キラキラ": ("kirakira", 10, "🍬"),
    "カチカチ": ("kachikachi", 10, "🧊"),
    "もちもち": ("mochimochi", 10, "🍡"),
    "ふわふわ": ("fuwafuwa", 10, "☁️")
}

def is_on_cooldown(last_time_str):
    if not last_time_str:
        return False, 0
    last_time = datetime.fromisoformat(last_time_str)
    now = datetime.utcnow()
    elapsed = now - last_time
    if elapsed < timedelta(hours=1):
        remaining = timedelta(hours=1) - elapsed
        return True, int(remaining.total_seconds() // 60)
    return False, 0

class PetView(View):
    def __init__(self, bot, author: discord.Member):
        super().__init__(timeout=None)
        self.bot = bot
        self.author = author

        for name, (key, exp, emoji) in FOOD_VALUES.items():
            self.add_item(self.FeedButton(label=name, style=discord.ButtonStyle.primary, emoji=emoji, key=key, exp=exp))

        self.add_item(self.PetButton(style=discord.ButtonStyle.secondary, emoji="🤗"))
        self.add_item(self.WalkButton(style=discord.ButtonStyle.success, emoji="🐾"))

    def load_pet(self):
        if not os.path.exists(PET_DATA_PATH):
            return {
                "personality": "ふわふわ",
                "mood": 50,
                "exp": {"kirakira": 0, "kachikachi": 0, "mochimochi": 0, "fuwafuwa": 0},
                "last_feed": {},
                "last_pet": {},
                "last_walk": {}
            }
        with open(PET_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_pet(self, pet):
        with open(PET_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(pet, f, ensure_ascii=False, indent=2)

    async def update_roles(self, guild: discord.Guild, user: discord.Member, total_exp: int):
        roles_to_remove = [ROLE_TITLE_10, ROLE_TITLE_30, ROLE_TITLE_50]
        roles_to_add = None
        if total_exp >= 50:
            roles_to_add = ROLE_TITLE_50
        elif total_exp >= 30:
            roles_to_add = ROLE_TITLE_30
        elif total_exp >= 10:
            roles_to_add = ROLE_TITLE_10

        # まず称号ロールを外す
        for role_id in roles_to_remove:
            role = guild.get_role(role_id)
            if role and role in user.roles:
                await user.remove_roles(role)

        # 条件を満たすロールを付与
        if roles_to_add:
            role = guild.get_role(roles_to_add)
            if role and role not in user.roles:
                await user.add_roles(role)

    class FeedButton(Button):
        def __init__(self, label, style, emoji, key, exp):
            super().__init__(label=label, style=style, emoji=emoji)
            self.key = key
            self.exp = exp

        async def callback(self, interaction: discord.Interaction):
            view: PetView = self.view
            user_id = str(interaction.user.id)
            pet = view.load_pet()
            pet.setdefault("last_feed", {})
            cooldown, mins = is_on_cooldown(pet["last_feed"].get(user_id))
            if cooldown:
                await interaction.response.send_message(f"⏳ {self.label}はあと{mins}分後にあげられます。", ephemeral=True)
                return

            pet["exp"][self.key] += self.exp
            pet["last_feed"][user_id] = datetime.utcnow().isoformat()
            pet["mood"] = min(100, pet.get("mood", 50) + 5)
            view.save_pet(pet)

            # 称号ロール更新
            total_exp = sum(pet.get("exp", {}).values())
            guild = interaction.guild
            user = interaction.user
            await view.update_roles(guild, user, total_exp)

            await interaction.response.send_message(f"{self.emoji} {self.label}をあげました！", ephemeral=True)

    class PetButton(Button):
        def __init__(self, style, emoji):
            super().__init__(label="撫でる", style=style, emoji=emoji)

        async def callback(self, interaction: discord.Interaction):
            view: PetView = self.view
            user_id = str(interaction.user.id)
            pet = view.load_pet()
            pet.setdefault("last_pet", {})
            cooldown, mins = is_on_cooldown(pet["last_pet"].get(user_id))
            if cooldown:
                await interaction.response.send_message(f"⏳ 撫でるのはあと{mins}分後にできます。", ephemeral=True)
                return

            pet["mood"] = min(100, pet.get("mood", 50) + 10)
            pet["last_pet"][user_id] = datetime.utcnow().isoformat()
            view.save_pet(pet)
            await interaction.response.send_message("🤗 撫でてあげました！ミルクシュガーは嬉しそうです！", ephemeral=True)

    class WalkButton(Button):
        def __init__(self, style, emoji):
            super().__init__(label="散歩", style=style, emoji=emoji)

        async def callback(self, interaction: discord.Interaction):
            view: PetView = self.view
            user_id = str(interaction.user.id)
            pet = view.load_pet()
            pet.setdefault("last_walk", {})
            cooldown, mins = is_on_cooldown(pet["last_walk"].get(user_id))
            if cooldown:
                await interaction.response.send_message(f"⏳ 散歩はあと{mins}分後にできます。", ephemeral=True)
                return

            pet["mood"] = min(100, pet.get("mood", 50) + 20)
            pet["last_walk"][user_id] = datetime.utcnow().isoformat()
            view.save_pet(pet)
            await interaction.response.send_message("🐾 散歩してきました！機嫌が上がりました！", ephemeral=True)

class PetGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pet")
    async def show_pet(self, ctx):
        if ctx.channel.id != PET_COMMAND_CHANNEL_ID:
            await ctx.send("このコマンドは指定チャンネルでのみ使用可能です。")
            return

        view = PetView(self.bot, ctx.author)
        pet = view.load_pet()
        total_exp = sum(pet.get("exp", {}).values())
        embed = discord.Embed(
            title="🐶 ミルクシュガーの育成",
            description=(
                f"性格: **{pet.get('personality', 'ふわふわ')}**\n"
                f"機嫌: {pet.get('mood', 50)}/100\n"
                f"経験値: {total_exp}"
            ),
            color=discord.Color.pink()
        )
        await ctx.send(embed=embed, view=view)

def setup(bot):
    bot.add_cog(PetGame(bot))
