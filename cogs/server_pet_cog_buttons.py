import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
from datetime import datetime, timedelta

from config import PET_CHANNEL_ID, FEED_TITLE_ROLES  # チャンネルIDと称号ロールIDをconfigから読み込み

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
            # 初期状態
            return {
                "personality": "ふわふわ",
                "mood": 50,
                "exp": {"kirakira": 0, "kachikachi": 0, "mochimochi": 0, "fuwafuwa": 0},
                "last_feed": {},
                "last_pet": {},
                "last_walk": {},
                "feed_counts": {}
            }
        with open(PET_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_pet(self, pet):
        with open(PET_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(pet, f, ensure_ascii=False, indent=2)

    class FeedButton(Button):
        def __init__(self, label, style, emoji, key, exp):
            super().__init__(label=label, style=style, emoji=emoji)
            self.key = key
            self.exp = exp

        async def callback(self, interaction: discord.Interaction):
            view: PetView = self.view
            user = interaction.user
            user_id = str(user.id)
            pet = view.load_pet()
            pet.setdefault("last_feed", {})
            pet.setdefault("feed_counts", {})

            cooldown, mins = is_on_cooldown(pet["last_feed"].get(user_id))
            if cooldown:
                await interaction.response.send_message(f"⏳ {self.label}はあと{mins}分後にあげられます。", ephemeral=True)
                return

            # 経験値と機嫌アップ
            pet["exp"][self.key] += self.exp
            pet["last_feed"][user_id] = datetime.utcnow().isoformat()
            pet["feed_counts"][user_id] = pet["feed_counts"].get(user_id, 0) + 1
            pet["mood"] = min(100, pet.get("mood", 50) + 5)
            view.save_pet(pet)

            # 称号ロールの更新
            await self.update_feed_title_role(user, pet["feed_counts"][user_id], interaction.guild)

            await interaction.response.send_message(f"{self.emoji} {self.label}をあげました！", ephemeral=True)

        async def update_feed_title_role(self, user: discord.Member, feed_count: int, guild: discord.Guild):
            roles_to_add = []
            roles_to_remove = []

            for count_threshold, role_id in FEED_TITLE_ROLES.items():
                role = guild.get_role(role_id)
                if not role:
                    continue
                if feed_count >= count_threshold:
                    roles_to_add.append(role)
                else:
                    roles_to_remove.append(role)

            # 不要な称号ロールを外す
            for role in roles_to_remove:
                if role in user.roles:
                    try:
                        await user.remove_roles(role, reason="餌やり称号更新のため")
                    except Exception:
                        pass

            # 最大の称号ロールだけ付与
            if roles_to_add:
                max_role = max(roles_to_add, key=lambda r: r.position)
                if max_role not in user.roles:
                    try:
                        await user.add_roles(max_role, reason="餌やり称号付与")
                    except Exception:
                        pass
                # 他のロールは外す
                for role in roles_to_add:
                    if role != max_role and role in user.roles:
                        try:
                            await user.remove_roles(role, reason="餌やり称号整理")
                        except Exception:
                            pass

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
        if ctx.channel.id != PET_CHANNEL_ID:
            await ctx.send("このコマンドは指定チャンネルでのみ使用可能です。")
            return

        view = PetView(self.bot, ctx.author)
        pet = view.load_pet()
        embed = discord.Embed(
            title="🐶 ミルクシュガーの育成",
            description=(
                f"性格: **{pet.get('personality', 'ふわふわ')}**\n"
                f"機嫌: {pet.get('mood', 50)}/100\n"
                f"経験値: {sum(pet.get('exp', {}).values())}"
            ),
            color=discord.Color.pink()
        )
        await ctx.send(embed=embed, view=view)

def setup(bot):
    bot.add_cog(PetGame(bot))
