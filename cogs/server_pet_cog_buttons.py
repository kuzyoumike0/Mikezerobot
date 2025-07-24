import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import json
import os
import datetime

# 設定ファイルから読み込み
from config import PET_HELP_CHANNEL_ID, PET_RANKING_CHANNEL_ID, PET_COMMAND_CHANNEL_ID, FEED_TITLE_ROLES

# ファイルパス設定
PET_DATA_PATH = "data/pets.json"
PET_IMAGES_PATH = "images"

# 餌やり・行動ごとの経験値
ACTION_VALUES = {
    "キラキラ": 10,
    "カチカチ": 10,
    "もちもち": 10,
    "散歩": 5,
    "撫でる": 3,
}

# 経験値→レベル変換しきい値
LEVEL_THRESHOLDS = {
    1: 0,
    2: 100,
    3: 200,
    4: 300,
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

# アクションボタン定義（餌やり・散歩・撫でる共通）
class ActionButton(Button):
    def __init__(self, label, bot):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.bot = bot
        self.action_type = label

    async def callback(self, interaction: discord.Interaction):
        try:
            server_id = str(interaction.guild.id)
            user_id = str(interaction.user.id)
            now = datetime.datetime.utcnow()

            pet_data = load_pet_data()
            if server_id not in pet_data:
                await interaction.response.send_message("⚠️ ペットがまだ生成されていません。`!pet`で開始してください。", ephemeral=True)
                return

            cooldown_key = f"last_{self.action_type}_{user_id}"
            last_action_time_str = pet_data[server_id].get(cooldown_key, "1970-01-01T00:00:00")
            last_action_time = datetime.datetime.fromisoformat(last_action_time_str)

            if (now - last_action_time).total_seconds() < 3600:
                await interaction.response.send_message(f"⏳ 「{self.action_type}」は1時間に1回だけです。", ephemeral=True)
                return

            pet_data[server_id]["exp"] = pet_data[server_id].get("exp", 0) + ACTION_VALUES.get(self.action_type, 0)
            pet_data[server_id][cooldown_key] = now.isoformat()

            user_stats = pet_data[server_id].setdefault("user_stats", {}).setdefault(user_id, {
                "feed_count": 0,
                "walk_count": 0,
                "pat_count": 0,
            })

            if self.action_type in ["キラキラ", "カチカチ", "もちもち"]:
                user_stats["feed_count"] += 1
            elif self.action_type == "散歩":
                user_stats["walk_count"] += 1
            elif self.action_type == "撫でる":
                user_stats["pat_count"] += 1

            member = interaction.user
            await update_feed_roles(member, user_stats["feed_count"])

            mood_boost = {
                "キラキラ": 5,
                "カチカチ": 5,
                "もちもち": 5,
                "散歩": 10,
                "撫でる": 7
            }.get(self.action_type, 0)
            pet_data[server_id]["mood"] = min(100, pet_data[server_id].get("mood", 50) + mood_boost)

            exp = pet_data[server_id]["exp"]
            level = get_pet_level(exp)
            mood = pet_data[server_id].get("mood", 50)

            image_filename = f"level{level}_pet.png"
            image_path = os.path.join(PET_IMAGES_PATH, image_filename)

            save_pet_data(pet_data)

            embed = discord.Embed(title="🐶 ミルクシュガーの様子", color=discord.Color.green())
            embed.add_field(name="📈 経験値", value=f"{exp} XP", inline=False)
            embed.add_field(name="🏅 あなたの餌やり数", value=f"{user_stats['feed_count']} 回", inline=True)
            embed.add_field(name="🚶 散歩回数", value=f"{user_stats['walk_count']} 回", inline=True)
            embed.add_field(name="🤗 撫でる回数", value=f"{user_stats['pat_count']} 回", inline=True)

            mood_status = "😄 機嫌良好" if mood >= 70 else "😐 普通" if mood >= 40 else "😞 不機嫌"
            embed.add_field(name="🧠 機嫌", value=f"{mood} / 100\n{mood_status}", inline=False)

            view = View()
            for action in ACTION_VALUES:
                view.add_item(ActionButton(action, self.bot))

            if os.path.exists(image_path):
                file = discord.File(image_path, filename=image_filename)
                embed.set_image(url=f"attachment://{image_filename}")
                await interaction.response.send_message(
                    content=f"{member.mention} が「{self.action_type}」をしました！",
                    embed=embed,
                    file=file,
                    view=view
                )
            else:
                embed.description = "⚠️ ペットの画像が見つかりません。"
                await interaction.response.send_message(
                    content=f"{member.mention} が「{self.action_type}」をしました！",
                    embed=embed,
                    view=view
                )
        except Exception as e:
            print(f"[ERROR] Interaction callback error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("⚠️ エラーが発生しました。管理者に連絡してください。", ephemeral=True)

class PetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_pet_image.start()
        self.mood_decay_loop.start()

    def cog_unload(self):
        self.update_pet_image.cancel()
        self.mood_decay_loop.cancel()

    @commands.command(name="pet")
    async def pet_command(self, ctx):
        # !petコマンドを特定チャンネルに制限する場合の例
        if ctx.channel.id != PET_COMMAND_CHANNEL_ID:
            await ctx.send(f"⚠️ このコマンドは <#{PET_COMMAND_CHANNEL_ID}> チャンネルでのみ使用可能です。")
            return

        server_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        pet_data = load_pet_data()

        if server_id not in pet_data:
            pet_data[server_id] = {
                "exp": 0,
                "last_image_change": "1970-01-01T00:00:00",
                "user_stats": {},
                "mood": 50
            }
            save_pet_data(pet_data)

        exp = pet_data[server_id].get("exp", 0)
        level = get_pet_level(exp)
        user_stats = pet_data[server_id].get("user_stats", {}).get(user_id, {"feed_count":0,"walk_count":0,"pat_count":0})
        mood = pet_data[server_id].get("mood", 50)

        image_filename = f"level{level}_pet.png"
        image_path = os.path.join(PET_IMAGES_PATH, image_filename)

        embed = discord.Embed(title="🐶 ミルクシュガーの様子だよ", color=discord.Color.green())
        embed.add_field(name="📈 経験値", value=f"{exp} XP", inline=False)
        embed.add_field(name="🏅 あなたの餌やり数", value=f"{user_stats.get('feed_count',0)} 回", inline=True)
        embed.add_field(name="🚶 散歩回数", value=f"{user_stats.get('walk_count',0)} 回", inline=True)
        embed.add_field(name="🤗 撫でる回数", value=f"{user_stats.get('pat_count',0)} 回", inline=True)

        mood_status = "😄 機嫌良好" if mood >= 70 else "😐 普通" if mood >= 40 else "😞 不機嫌"
        embed.add_field(name="🧠 機嫌", value=f"{mood} / 100\n{mood_status}", inline=False)

        view = View()
        for action in ACTION_VALUES:
            view.add_item(ActionButton(action, self.bot))

        if os.path.exists(image_path):
            file = discord.File(image_path, filename=image_filename)
            embed.set_image(url=f"attachment://{image_filename}")
            await ctx.send(embed=embed, file=file, view=view)
        else:
            embed.description = "⚠️ ペットの画像が見つかりません。"
            await ctx.send(embed=embed, view=view)

    @commands.command(name="pet_ranking")
    async def pet_ranking_command(self, ctx):
        if ctx.channel.id != PET_RANKING_CHANNEL_ID:
            await ctx.send(f"⚠️ このコマンドは <#{PET_RANKING_CHANNEL_ID}> チャンネルでのみ使用可能です。")
            return

        server_id = str(ctx.guild.id)
        pet_data = load_pet_data()

        if server_id not in pet_data or "user_stats" not in pet_data[server_id]:
            await ctx.send("⚠️ まだ餌をあげたユーザーがいません。")
            return

        feed_counts = {uid: stats.get("feed_count", 0) for uid, stats in pet_data[server_id]["user_stats"].items()}
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

    @commands.command(name="pet_help")
    async def pet_help_command(self, ctx):
        if ctx.channel.id != PET_HELP_CHANNEL_ID:
            await ctx.send(f"⚠️ このコマンドは <#{PET_HELP_CHANNEL_ID}> チャンネルでのみ使用可能です。")
            return

        embed = discord.Embed(
            title="🐶 ペットコマンド一覧",
            description=(
                "`!pet` - ペットの状態を表示し、餌やり・散歩・撫でるボタンを表示します。\n"
                "`!pet_ranking` - サーバー内の餌やりランキングを表示します。\n"
                "`!pet_help` - このコマンド一覧を表示します。"
            ),
            color=discord.Color.blue()
        )
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

    @tasks.loop(minutes=180)  # 3時間ごとに機嫌を下げる
    async def mood_decay_loop(self):
        pet_data = load_pet_data()
        updated = False
        for server_id, data in pet_data.items():
            current_mood = data.get("mood", 50)
            new_mood = max(0, current_mood - 2)
            if new_mood != current_mood:
                data["mood"] = new_mood
                updated = True
        if updated:
            save_pet_data(pet_data)

    @mood_decay_loop.before_loop
    async def before_mood_decay_loop(self):
        await self.bot.wait_until_ready()

# コグ登録
async def setup(bot: commands.Bot):
    await bot.add_cog(PetCog(bot))
