import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import json
import os
import datetime

# 設定ファイルからIDやロール情報を読み込み（別途用意されたconfig.pyから）
from config import PET_HELP_CHANNEL_ID, PET_RANKING_CHANNEL_ID, PET_COMMAND_CHANNEL_ID, FEED_TITLE_ROLES

# データ保存用のファイルパス
PET_DATA_PATH = "data/pets.json"
PET_IMAGES_PATH = "images"

# アクションごとの経験値テーブル
ACTION_VALUES = {
    "キラキラ": 10,
    "カチカチ": 10,
    "もちもち": 10,
    "散歩": 5,
    "撫でる": 3,
}

# 経験値に応じたレベルの閾値
LEVEL_THRESHOLDS = {
    1: 0,
    2: 100,
    3: 200,
    4: 300,
}

# 経験値からレベルを計算する関数
def get_pet_level(exp: int):
    # 高いレベル順に閾値をチェックし、条件を満たしたらそのレベルを返す
    for level in sorted(LEVEL_THRESHOLDS.keys(), reverse=True):
        if exp >= LEVEL_THRESHOLDS[level]:
            return level
    return 1  # 最低レベル

# 保存されたペットデータをJSONファイルから読み込む
def load_pet_data():
    if not os.path.exists(PET_DATA_PATH):
        return {}  # ファイルがなければ空の辞書を返す
    with open(PET_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ペットデータをJSON形式でファイルに保存
def save_pet_data(data):
    os.makedirs(os.path.dirname(PET_DATA_PATH), exist_ok=True)  # フォルダがなければ作成
    with open(PET_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# 餌やり回数に応じて称号ロールを付与・削除する処理
async def update_feed_roles(member: discord.Member, feed_count: int):
    try:
        # FEED_TITLE_ROLES は閾値(int) : ロールID の辞書
        for threshold, role_id in FEED_TITLE_ROLES.items():
            role = member.guild.get_role(role_id)
            if not role:
                continue  # ロールが存在しなければスキップ

            if feed_count >= threshold:
                # 閾値以上ならロールを付与（まだ持っていなければ）
                if role not in member.roles:
                    await member.add_roles(role, reason="餌やり称号ロール付与")
            else:
                # 閾値未満ならロールを削除（持っていたら）
                if role in member.roles:
                    await member.remove_roles(role, reason="餌やり称号ロール削除")
    except Exception as e:
        print(f"[ERROR] ロール更新失敗: {e}")

# 各アクション（キラキラ、カチカチ、もちもち、散歩、撫でる）を表すボタン
class ActionButton(Button):
    def __init__(self, label, bot):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.bot = bot
        self.action_type = label  # ボタンのラベルをアクション名として扱う

    # ボタンが押された時の処理
    async def callback(self, interaction: discord.Interaction):
        try:
            server_id = str(interaction.guild.id)
            user_id = str(interaction.user.id)
            now = datetime.datetime.utcnow()

            pet_data = load_pet_data()
            if server_id not in pet_data:
                # ペットがまだ生成されていない場合はエラーメッセージ
                await interaction.response.send_message("⚠️ ペットがまだ生成されていません。`!pet`で開始してください。", ephemeral=True)
                return

            # 1時間のクールダウン管理用キー
            cooldown_key = f"last_{self.action_type}_{user_id}"
            last_action_time_str = pet_data[server_id].get(cooldown_key, "1970-01-01T00:00:00")
            last_action_time = datetime.datetime.fromisoformat(last_action_time_str)

            # クールダウン判定：1時間以内は行動不可
            if (now - last_action_time).total_seconds() < 3600:
                await interaction.response.send_message(f"⏳ 「{self.action_type}」は1時間に1回だけです。", ephemeral=True)
                return

            # 経験値加算
            pet_data[server_id]["exp"] = pet_data[server_id].get("exp", 0) + ACTION_VALUES.get(self.action_type, 0)
            pet_data[server_id][cooldown_key] = now.isoformat()

            # ユーザー統計情報を取得・初期化
            user_stats = pet_data[server_id].setdefault("user_stats", {}).setdefault(user_id, {
                "feed_count": 0,
                "walk_count": 0,
                "pat_count": 0,
            })

            # アクションごとに該当するカウントを増やす
            if self.action_type in ["キラキラ", "カチカチ", "もちもち"]:
                user_stats["feed_count"] += 1
            elif self.action_type == "散歩":
                user_stats["walk_count"] += 1
            elif self.action_type == "撫でる":
                user_stats["pat_count"] += 1

            # 餌やり回数に応じて称号ロールを更新
            member = interaction.user
            await update_feed_roles(member, user_stats["feed_count"])

            # 機嫌値の増加量をアクションごとに設定
            mood_boost = {
                "キラキラ": 5,
                "カチカチ": 5,
                "もちもち": 5,
                "散歩": 10,
                "撫でる": 7
            }.get(self.action_type, 0)

            # 機嫌(mood)は最大100まで
            pet_data[server_id]["mood"] = min(100, pet_data[server_id].get("mood", 50) + mood_boost)

            # 現在の経験値・レベル・機嫌を取得
            exp = pet_data[server_id]["exp"]
            level = get_pet_level(exp)
            mood = pet_data[server_id].get("mood", 50)

            # レベルに応じた画像ファイルのパスを設定
            image_filename = f"level{level}_pet.png"
            image_path = os.path.join(PET_IMAGES_PATH, image_filename)

            # 変更を保存
            save_pet_data(pet_data)

            # 埋め込みメッセージを作成
            embed = discord.Embed(title="🐶 ミルクシュガーの様子", color=discord.Color.green())
            embed.add_field(name="📈 経験値", value=f"{exp} XP", inline=False)
            embed.add_field(name="🏅 あなたの餌やり数", value=f"{user_stats['feed_count']} 回", inline=True)
            embed.add_field(name="🚶 散歩回数", value=f"{user_stats['walk_count']} 回", inline=True)
            embed.add_field(name="🤗 撫でる回数", value=f"{user_stats['pat_count']} 回", inline=True)

            # 機嫌の状態をわかりやすく表示
            mood_status = "😄 機嫌良好" if mood >= 70 else "😐 普通" if mood >= 40 else "😞 不機嫌"
            embed.add_field(name="🧠 機嫌", value=f"{mood} / 100\n{mood_status}", inline=False)

            # ボタン付きのView（操作UI）を作成し、すべてのアクションボタンを追加
            view = View()
            for action in ACTION_VALUES:
                view.add_item(ActionButton(action, self.bot))

            # 画像ファイルが存在すれば画像付きで送信
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
                # 画像がない場合はテキストのみ送信
                embed.description = "⚠️ ペットの画像が見つかりません。"
                await interaction.response.send_message(
                    content=f"{member.mention} が「{self.action_type}」をしました！",
                    embed=embed,
                    view=view
                )
        except Exception as e:
            # エラー処理
            print(f"[ERROR] Interaction callback error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("⚠️ エラーが発生しました。管理者に連絡してください。", ephemeral=True)

# ペット機能全般をまとめたCogクラス
class PetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 3時間ごとに画像を更新チェックするタスク開始
        self.update_pet_image.start()
        # 3時間ごとに機嫌を下げるタスク開始
        self.mood_decay_loop.start()

    # コグがアンロードされる際にタスクを停止
    def cog_unload(self):
        self.update_pet_image.cancel()
        self.mood_decay_loop.cancel()

    # !pet コマンド：ペットの状態表示とアクションボタン表示
    @commands.command(name="pet")
    async def pet_command(self, ctx):
        # コマンド実行を特定チャンネルに制限
        if ctx.channel.id != PET_COMMAND_CHANNEL_ID:
            await ctx.send(f"⚠️ このコマンドは <#{PET_COMMAND_CHANNEL_ID}> チャンネルでのみ使用可能です。")
            return

        server_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        pet_data = load_pet_data()

        # サーバーにペットデータがなければ初期化
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

        # アクションボタンをすべて追加したビュー作成
        view = View()
        for action in ACTION_VALUES:
            view.add_item(ActionButton(action, self.bot))

        # 画像があれば添付して送信、なければテキストのみ
        if os.path.exists(image_path):
            file = discord.File(image_path, filename=image_filename)
            embed.set_image(url=f"attachment://{image_filename}")
            await ctx.send(embed=embed, file=file, view=view)
        else:
            embed.description = "⚠️ ペットの画像が見つかりません。"
            await ctx.send(embed=embed, view=view)

    # !pet_ranking コマンド：餌やりランキングを表示
    @commands.command(name="pet_ranking")
    async def pet_ranking_command(self, ctx):
        # 実行を特定チャンネルに制限
        if ctx.channel.id != PET_RANKING_CHANNEL_ID:
            await ctx.send(f"⚠️ このコマンドは <#{PET_RANKING_CHANNEL_ID}> チャンネルでのみ使用可能です。")
            return

        server_id = str(ctx.guild.id)
        pet_data = load_pet_data()

        # 餌やりユーザーがいなければメッセージ送信
        if server_id not in pet_data or "user_stats" not in pet_data[server_id]:
            await ctx.send("⚠️ まだ餌をあげたユーザーがいません。")
            return

        # 餌やり回数でソート
        feed_counts = {uid: stats.get("feed_count", 0) for uid, stats in pet_data[server_id]["user_stats"].items()}
        sorted_feed = sorted(feed_counts.items(), key=lambda x: x[1], reverse=True)

        embed = discord.Embed(
            title="🏆 餌やりランキング",
            description="上位の餌やり名人たち！",
            color=discord.Color.gold()
        )

        # 上位10人のニックネームを取得し表示
        for idx, (user_id, count) in enumerate(sorted_feed[:10], start=1):
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else f"ユーザーID:{user_id}"
            embed.add_field(name=f"{idx}位: {name}", value=f"{count} 回", inline=False)

        await ctx.send(embed=embed)

    # !pet_help コマンド：コマンド一覧を表示
    @commands.command(name="pet_help")
    async def pet_help_command(self, ctx):
        # 実行を特定チャンネルに制限
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

    # 1分ごとにペット画像の更新が必要かチェックするタスク
    @tasks.loop(minutes=1)
    async def update_pet_image(self):
        now = datetime.datetime.utcnow()
        pet_data = load_pet_data()
        updated = False

        for server_id, data in pet_data.items():
            last_change = datetime.datetime.fromisoformat(data.get("last_image_change", "1970-01-01T00:00:00"))
            # 最終更新から3時間経過していれば更新フラグON
            if (now - last_change).total_seconds() >= 10800:  # 10800秒 = 3時間
                data["last_image_change"] = now.isoformat()
                updated = True

        if updated:
            save_pet_data(pet_data)

    # update_pet_image タスク起動前の準備
    @update_pet_image.before_loop
    async def before_update_pet_image(self):
        await self.bot.wait_until_ready()

    # 3時間ごとに機嫌値を減少させるタスク
    @tasks.loop(minutes=180)
    async def mood_decay_loop(self):
        pet_data = load_pet_data()
        updated = False
        for server_id, data in pet_data.items():
            current_mood = data.get("mood", 50)
            new_mood = max(0, current_mood - 2)  # 機嫌は0未満にならない
            if new_mood != current_mood:
                data["mood"] = new_mood
                updated = True
        if updated:
            save_pet_data(pet_data)

    # mood_decay_loop タスク起動前の準備
    @mood_decay_loop.before_loop
    async def before_mood_decay_loop(self):
        await self.bot.wait_until_ready()

# BotにCogをセットアップする関数（cogsの読み込み時に呼ばれる）
async def setup(bot: commands.Bot):
    await bot.add_cog(PetCog(bot))
