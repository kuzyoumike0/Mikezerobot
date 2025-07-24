import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import json
import os
import datetime

# ペットデータの保存場所
PET_DATA_PATH = "data/pets.json"
# ペット画像フォルダ
PET_IMAGES_PATH = "images"

# アクション別の経験値
ACTION_EXP = {
    "キラキラ": 10,
    "カチカチ": 10,
    "もちもち": 10,
    "ふわふわ": 10,
    "散歩": 5,
    "撫でる": 7,
}

# 餌が進化に必要な数
EVOLVE_THRESHOLD = 100

# 進化可能な餌の種類（優先順位順）
EVOLVE_ORDER = ["もちもち", "カチカチ", "キラキラ", "ふわふわ"]

# 画像ファイル名対応
IMAGE_FILES = {
    "もちもち": "pet_mochimochi.png",
    "カチカチ": "pet_kachikachi.png",
    "キラキラ": "pet_kirakira.png",
    "ふわふわ": "pet_fuwafuwa.png",
}

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

# 進化判定・画像更新関数
def check_and_update_evolution(pet_data, guild_id):
    data = pet_data[guild_id]
    # 餌のカウントを取得（なければ0）
    feed_counts = {k: data.get(f"feed_{k}", 0) for k in IMAGE_FILES.keys()}
    total_feed = sum(feed_counts.values())

    # 画像更新は1時間に1回までに制限
    now = datetime.datetime.utcnow()
    last_change_str = data.get("last_image_change", "1970-01-01T00:00:00")
    last_change = datetime.datetime.fromisoformat(last_change_str)
    if (now - last_change).total_seconds() < 3600:
        # 1時間経っていなければ画像更新しない
        return

    # 100個以上の餌があれば進化判定
    if total_feed >= EVOLVE_THRESHOLD:
        # 最も多く与えられた餌の種類で進化（優先順位に従う）
        max_feed_type = None
        max_feed_count = -1
        for kind in EVOLVE_ORDER:
            if feed_counts[kind] > max_feed_count:
                max_feed_count = feed_counts[kind]
                max_feed_type = kind

        if max_feed_type:
            # 画像を進化させる
            data["current_image"] = IMAGE_FILES[max_feed_type]
            # 餌カウントは100個分を減らす（繰り返し可能）
            for kind in IMAGE_FILES.keys():
                data[f"feed_{kind}"] = max(0, data.get(f"feed_{kind}", 0) - EVOLVE_THRESHOLD)
            data["last_image_change"] = now.isoformat()
            save_pet_data(pet_data)

# ボタンクラス（各アクション用）
class ActionButton(Button):
    def __init__(self, label, bot):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.bot = bot
        self.action = label

    async def callback(self, interaction: discord.Interaction):
        try:
            guild_id = str(interaction.guild.id)
            user_id = str(interaction.user.id)
            now = datetime.datetime.utcnow()

            pet_data = load_pet_data()

            if guild_id not in pet_data:
                await interaction.response.send_message("⚠️ ペットがまだ生成されていません。`!pet`コマンドで開始してください。", ephemeral=True)
                return

            # 餌の場合はユーザー単位で1時間に1回まで制限
            if self.action in IMAGE_FILES.keys():
                cooldown_key = f"last_feed_{user_id}"
                last_time_str = pet_data[guild_id].get(cooldown_key, "1970-01-01T00:00:00")
                last_time = datetime.datetime.fromisoformat(last_time_str)
                if (now - last_time).total_seconds() < 3600:
                    await interaction.response.send_message(f"⏳ 餌は1時間に1回だけあげられます。", ephemeral=True)
                    return
                # クールダウン更新
                pet_data[guild_id][cooldown_key] = now.isoformat()
            else:
                # 散歩や撫でるは個別制限なし（必要ならここで追加可能）
                pass

            # 経験値加算
            exp_add = ACTION_EXP.get(self.action, 0)
            pet_data[guild_id]["exp"] = pet_data[guild_id].get("exp", 0) + exp_add

            # 餌カウント増加（餌の場合）
            if self.action in IMAGE_FILES.keys():
                key = f"feed_{self.action}"
                pet_data[guild_id][key] = pet_data[guild_id].get(key, 0) + 1

            # ユーザースタッツ更新
            user_stats = pet_data[guild_id].setdefault("user_stats", {}).setdefault(user_id, {
                "feed_count": 0,
                "walk_count": 0,
                "pat_count": 0,
            })

            # アクション別カウント増加
            if self.action in IMAGE_FILES.keys():
                user_stats["feed_count"] += 1
            elif self.action == "散歩":
                user_stats["walk_count"] += 1
            elif self.action == "撫でる":
                user_stats["pat_count"] += 1

            # 機嫌値の増加設定
            mood_boost = {
                "キラキラ": 5,
                "カチカチ": 5,
                "もちもち": 5,
                "ふわふわ": 5,
                "散歩": 10,
                "撫でる": 7
            }.get(self.action, 0)

            # 機嫌(mood)は最大100まで
            pet_data[guild_id]["mood"] = min(100, pet_data[guild_id].get("mood", 50) + mood_boost)

            # 進化判定・画像更新
            check_and_update_evolution(pet_data, guild_id)

            # 現在の画像ファイル名
            image_file = pet_data[guild_id].get("current_image", IMAGE_FILES["ふわふわ"])
            image_path = os.path.join(PET_IMAGES_PATH, image_file)

            # データ保存
            save_pet_data(pet_data)

            # 埋め込み作成
            exp = pet_data[guild_id]["exp"]
            mood = pet_data[guild_id].get("mood", 50)

            mood_status = "😄 機嫌良好" if mood >= 70 else "😐 普通" if mood >= 40 else "😞 不機嫌"
            if mood >= 70:
                personality = "元気いっぱい"
            elif mood >= 40:
                personality = "普通"
            else:
                personality = "ちょっと不機嫌"

            embed = discord.Embed(title="🐶 ミルクシュガーの様子", color=discord.Color.green())
            embed.add_field(name="📈 経験値", value=f"{exp} XP", inline=False)
            embed.add_field(name="🏅 あなたの餌やり数", value=f"{user_stats['feed_count']} 回", inline=True)
            embed.add_field(name="🚶 散歩回数", value=f"{user_stats['walk_count']} 回", inline=True)
            embed.add_field(name="🤗 撫でる回数", value=f"{user_stats['pat_count']} 回", inline=True)
            embed.add_field(name="🧠 機嫌", value=f"{mood} / 100\n{mood_status}", inline=False)
            embed.add_field(name="💖 性格", value=personality, inline=False)

            # ボタン付きView作成
            view = View()
            for action in ACTION_EXP.keys():
                view.add_item(ActionButton(action, self.bot))

            # 画像があれば添付
            if os.path.exists(image_path):
                file = discord.File(image_path, filename=image_file)
                embed.set_image(url=f"attachment://{image_file}")
                await interaction.response.send_message(content=f"{interaction.user.mention} が「{self.action}」しました！", embed=embed, file=file, view=view)
            else:
                embed.description = "⚠️ ペットの画像が見つかりません。"
                await interaction.response.send_message(content=f"{interaction.user.mention} が「{self.action}」しました！", embed=embed, view=view)

        except Exception as e:
            print(f"[ERROR] ActionButton callback: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("⚠️ エラーが発生しました。", ephemeral=True)

# Cog本体
class PetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_image_loop.start()
        self.mood_decay_loop.start()

    # !pet コマンド - ペット状態＆操作ボタン表示
    @commands.command(name="pet")
    async def pet_command(self, ctx):
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        pet_data = load_pet_data()

        if guild_id not in pet_data:
            # 初期データ作成
            pet_data[guild_id] = {
                "exp": 0,
                "last_image_change": "1970-01-01T00:00:00",
                "user_stats": {},
                "mood": 50,
                "current_image": IMAGE_FILES["ふわふわ"],  # 初期画像はふわふわ
            }
            # 餌カウント初期化
            for kind in IMAGE_FILES.keys():
                pet_data[guild_id][f"feed_{kind}"] = 0

            save_pet_data(pet_data)

        # 進化判定（起動時にも反映）
        check_and_update_evolution(pet_data, guild_id)

        exp = pet_data[guild_id].get("exp", 0)
        mood = pet_data[guild_id].get("mood", 50)
        user_stats = pet_data[guild_id].get("user_stats", {}).get(user_id, {"feed_count":0,"walk_count":0,"pat_count":0})

        image_file = pet_data[guild_id].get("current_image", IMAGE_FILES["ふわふわ"])
        image_path = os.path.join(PET_IMAGES_PATH, image_file)

        mood_status = "😄 機嫌良好" if mood >= 70 else "😐 普通" if mood >= 40 else "😞 不機嫌"
        if mood >= 70:
            personality = "元気いっぱい"
        elif mood >= 40:
            personality = "普通"
        else:
            personality = "ちょっと不機嫌"

        embed = discord.Embed(title="🐶 ミルクシュガーの様子だよ", color=discord.Color.green())
        embed.add_field(name="📈 経験値", value=f"{exp} XP", inline=False)
        embed.add_field(name="🏅 あなたの餌やり数", value=f"{user_stats.get('feed_count',0)} 回", inline=True)
        embed.add_field(name="🚶 散歩回数", value=f"{user_stats.get('walk_count',0)} 回", inline=True)
        embed.add_field(name="🤗 撫でる回数", value=f"{user_stats.get('pat_count',0)} 回", inline=True)
        embed.add_field(name="🧠 機嫌", value=f"{mood} / 100\n{mood_status}", inline=False)
        embed.add_field(name="💖 性格", value=personality, inline=False)

        view = View()
        for action in ACTION_EXP.keys():
            view.add_item(ActionButton(action, self.bot))

        if os.path.exists(image_path):
            file = discord.File(image_path, filename=image_file)
            embed.set_image(url=f"attachment://{image_file}")
            await ctx.send(embed=embed, file=file, view=view)
        else:
            embed.description = "⚠️ ペットの画像が見つかりません。"
            await ctx.send(embed=embed, view=view)

    # !pet_ranking コマンド - 餌やりランキング表示
    @commands.command(name="pet_ranking")
    async def pet_ranking_command(self, ctx):
        guild_id = str(ctx.guild.id)
        pet_data = load_pet_data()

        if guild_id not in pet_data or "user_stats" not in pet_data[guild_id]:
            await ctx.send("⚠️ まだ餌をあげたユーザーがいません。")
            return

        feed_counts = {uid: stats.get("feed_count",0) for uid, stats in pet_data[guild_id]["user_stats"].items()}
        sorted_feed = sorted(feed_counts.items(), key=lambda x: x[1], reverse=True)

        embed = discord.Embed(title="🏆 餌やりランキング", description="上位の餌やり名人たち！", color=discord.Color.gold())

        for i, (user_id, count) in enumerate(sorted_feed[:10], start=1):
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else f"ユーザーID:{user_id}"
            embed.add_field(name=f"{i}位: {name}", value=f"{count} 回", inline=False)

        await ctx.send(embed=embed)

    # !pet_help コマンド - ヘルプ表示
    @commands.command(name="pet_help")
    async def pet_help_command(self, ctx):
        embed = discord.Embed(
            title="🐶 ペットコマンド一覧",
            description=(
                "`!pet` - ペットの状態を表示し、操作ボタンを表示します。\n"
                "`!pet_ranking` - 餌やりランキングを表示します。\n"
                "`!pet_help` - このヘルプを表示します。"
            ),
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    # 3時間ごとに画像更新日時をリセット（任意で機能を残す）
    @tasks.loop(minutes=180)
    async def update_image_loop(self):
        pet_data = load_pet_data()
        updated = False
        now = datetime.datetime.utcnow()
        for guild_id, data in pet_data.items():
            last_change = datetime.datetime.fromisoformat(data.get("last_image_change","1970-01-01T00:00:00"))
            if (now - last_change).total_seconds() >= 10800:
                data["last_image_change"] = now.isoformat()
                updated = True
        if updated:
            save_pet_data(pet_data)

    @update_image_loop.before_loop
    async def before_update_image_loop(self):
        await self.bot.wait_until_ready()

    # 2時間ごとに機嫌値を-10（0未満禁止）
    @tasks.loop(minutes=120)
    async def mood_decay_loop(self):
        pet_data = load_pet_data()
        updated = False
        for guild_id, data in pet_data.items():
            current_mood = data.get("mood", 50)
            new_mood = max(0, current_mood - 10)
            if new_mood != current_mood:
                data["mood"] = new_mood
                updated = True
        if updated:
            save_pet_data(pet_data)

    @mood_decay_loop.before_loop
    async def before_mood_decay_loop(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.update_image_loop.cancel()
        self.mood_decay_loop.cancel()

async def setup(bot):
    await bot.add_cog(PetCog(bot))
