import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import json
import os
import datetime

# ファイルパス設定
PET_DATA_PATH = "data/pets.json"
PET_IMAGES_PATH = "images"

# 餌の種類と経験値
FOOD_VALUES = {
    "キラキラ": 10,
    "カチカチ": 10,
    "もちもち": 10,
}

# 経験値→レベル変換しきい値
LEVEL_THRESHOLDS = {
    1: 0,
    2: 100,
    3: 200,
    4: 300,
}

# 餌やり回数に応じたロールID（称号）
FEED_TITLE_ROLES = {
    10: 1397793352396574720,  # 10回
    30: 1397793748926201886,  # 30回
    50: 1397794033236971601,  # 50回
}

# レベル取得関数
def get_pet_level(exp: int):
    for level in sorted(LEVEL_THRESHOLDS.keys(), reverse=True):
        if exp >= LEVEL_THRESHOLDS[level]:
            return level
    return 1

# ペットデータ読み込み
def load_pet_data():
    if not os.path.exists(PET_DATA_PATH):
        return {}
    with open(PET_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ペットデータ保存
def save_pet_data(data):
    os.makedirs(os.path.dirname(PET_DATA_PATH), exist_ok=True)
    with open(PET_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# 称号ロールの更新
async def update_feed_roles(member: discord.Member, feed_count: int):
    try:
        for threshold, role_id in FEED_TITLE_ROLES.items():
            role = member.guild.get_role(role_id)
            if not role:
                continue

            if feed_count >= threshold:
                if role not in member.roles:
                    await member.add_roles(role, reason="餌やり称号ロール付与")
            else:
                if role in member.roles:
                    await member.remove_roles(role, reason="餌やり称号ロール削除")
    except Exception as e:
        print(f"[ERROR] ロール更新失敗: {e}")

# 餌やりボタン
class FoodButton(Button):
    def __init__(self, label, bot):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.bot = bot
        self.food_type = label

    async def callback(self, interaction: discord.Interaction):
        try:
            server_id = str(interaction.guild.id)
            user_id = str(interaction.user.id)
            now = datetime.datetime.utcnow()

            pet_data = load_pet_data()
            if server_id not in pet_data:
                await interaction.response.send_message("⚠️ ペットがまだ生成されていません。`!pet`で開始してください。", ephemeral=True)
                return

            last_fed_by = pet_data[server_id].get("last_fed_by", {}).get(user_id, "1970-01-01T00:00:00")
            last_fed_time = datetime.datetime.fromisoformat(last_fed_by)

            if (now - last_fed_time).total_seconds() < 3600:
                await interaction.response.send_message("⏳ あなたはまだ餌を与えられません。1時間に1回だけです。", ephemeral=True)
                return

            pet_data[server_id]["exp"] += FOOD_VALUES[self.food_type]
            pet_data[server_id].setdefault("last_fed_by", {})[user_id] = now.isoformat()
            pet_data[server_id].setdefault("feed_count", {}).setdefault(user_id, 0)
            pet_data[server_id]["feed_count"][user_id] += 1

            exp = pet_data[server_id]["exp"]
            level = get_pet_level(exp)
            feed_count = pet_data[server_id]["feed_count"][user_id]
            image_filename = f"level{level}_pet.png"
            image_path = os.path.join(PET_IMAGES_PATH, image_filename)

            save_pet_data(pet_data)

            embed = discord.Embed(title="🐶 ミルクシュガーの様子だよ", color=discord.Color.green())
            embed.add_field(name="📈 経験値", value=f"{exp} XP", inline=False)
            embed.add_field(name="🏅 あなたの餌やり数", value=f"{feed_count} 回", inline=False)

            view = View()
            for food in FOOD_VALUES:
                view.add_item(FoodButton(food, self.bot))

            member = interaction.user
            await update_feed_roles(member, feed_count)

            if os.path.exists(image_path):
                file = discord.File(image_path, filename=image_filename)
                await interaction.response.send_message(
                    content=f"{member.mention} が「{self.food_type}」をあげました！",
                    embed=embed,
                    file=file,
                    view=view
                )
            else:
                embed.description = "⚠️ ペットの画像が見つかりません。"
                await interaction.response.send_message(
                    content=f"{member.mention} が「{self.food_type}」をあげました！",
                    embed=embed,
                    view=view
                )
        except Exception as e:
            print(f"[ERROR] Interaction callback error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("⚠️ エラーが発生しました。管理者に連絡してください。", ephemeral=True)

# ペット機能全体
class PetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_pet_image.start()

    def cog_unload(self):
        self.update_pet_image.cancel()

    @commands.command(name="pet")
    async def pet_command(self, ctx):
        server_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        pet_data = load_pet_data()

        if server_id not in pet_data:
            pet_data[server_id] = {
                "exp": 0,
                "last_image_change": "1970-01-01T00:00:00",
                "last_fed_by": {},
                "feed_count": {}
            }
            save_pet_data(pet_data)

        exp = pet_data[server_id]["exp"]
        level = get_pet_level(exp)
        feed_count = pet_data[server_id].get("feed_count", {}).get(user_id, 0)
        image_filename = f"level{level}_pet.png"
        image_path = os.path.join(PET_IMAGES_PATH, image_filename)

        embed = discord.Embed(title="🐶 サーバーペットの様子", color=discord.Color.green())
        embed.add_field(name="📈 経験値", value=f"{exp} XP", inline=False)
        embed.add_field(name="🏅 あなたの餌やり数", value=f"{feed_count} 回", inline=False)

        view = View()
        for food in FOOD_VALUES:
            view.add_item(FoodButton(food, self.bot))

        if os.path.exists(image_path):
            file = discord.File(image_path, filename=image_filename)
            embed.set_image(url=f"attachment://{image_filename}")
            await ctx.send(embed=embed, file=file, view=view)
        else:
            embed.description = "⚠️ ペットの画像が見つかりません。"
            await ctx.send(embed=embed, view=view)

    @commands.command(name="pet_ranking")
    async def pet_ranking_command(self, ctx):
        server_id = str(ctx.guild.id)
        pet_data = load_pet_data()

        if server_id not in pet_data or "feed_count" not in pet_data[server_id]:
            await ctx.send("⚠️ まだ餌をあげたユーザーがいません。")
            return

        feed_counts = pet_data[server_id]["feed_count"]
        sorted_feed = sorted(feed_counts.items(), key=lambda x: x[1], reverse=True)

        embed = discord.Embed(
            title="🏆 餌やりランキング",
            description="上位の餌やり名人たち！",
            color=discord.Color.gold()
        )

        for idx, (user_id, count) in enumerate(sorted_feed[:10], start=1):
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else f"ユーザーID:{user_id}"
            embed.add_field(name=f"{idx}位: {name}", value=f"{count} 回", inline=False)

        await ctx.send(embed=embed)

    @tasks.loop(minutes=1)
    async def update_pet_image(self):
        now = datetime.datetime.utcnow()
        pet_data = load_pet_data()
        updated = False

        for server_id, data in pet_data.items():
            last_change = datetime.datetime.fromisoformat(data.get("last_image_change", "1970-01-01T00:00:00"))
            if (now - last_change).total_seconds() >= 10800:
                data["last_image_change"] = now.isoformat()
                updated = True

        if updated:
            save_pet_data(pet_data)

    @update_pet_image.before_loop
    async def before_update_pet_image(self):
        await self.bot.wait_until_ready()

# コグ登録
async def setup(bot: commands.Bot):
    await bot.add_cog(PetCog(bot))
