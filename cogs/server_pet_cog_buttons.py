import discord
from discord.ext import commands
import os
import datetime
import json
import traceback

# 既存の設定・関数を前提とします
PET_DATA_PATH = "data/pets.json"
PET_IMAGES_PATH = "images"

IMAGE_FILES = {
    "もちもち": "pet_mochimochi.png",
    "カチカチ": "pet_kachikachi.png",
    "キラキラ": "pet_kirakira.png",
    "ふわふわ": "pet_fuwafuwa.png",
}

PERSONALITY_MAP = {
    "キラキラ": "キラキラ",
    "カチカチ": "カチカチ",
    "もちもち": "もちもち",
    "ふわふわ": "まるまる"
}

EVOLVE_THRESHOLD = 100
EVOLVE_ORDER = ["もちもち", "カチカチ", "キラキラ", "ふわふわ"]

def load_pet_data():
    try:
        if not os.path.exists(PET_DATA_PATH):
            print("[load_pet_data] データファイルが存在しません。新規作成用に空データ返却")
            return {}
        with open(PET_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"[load_pet_data] データ読み込み成功: {len(data)} ギルド分")
            return data
    except Exception as e:
        print(f"[load_pet_data] エラー発生: {e}")
        traceback.print_exc()
        return {}

def save_pet_data(data):
    try:
        os.makedirs(os.path.dirname(PET_DATA_PATH), exist_ok=True)
        with open(PET_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("[save_pet_data] データ保存成功")
    except Exception as e:
        print(f"[save_pet_data] エラー発生: {e}")
        traceback.print_exc()

def check_and_update_evolution(pet_data, guild_id):
    try:
        data = pet_data[guild_id]
        feed_counts = {k: data.get(f"feed_{k}", 0) for k in IMAGE_FILES.keys()}
        total_feed = sum(feed_counts.values())
        print(f"[check_and_update_evolution] ギルドID: {guild_id} 総餌数: {total_feed} 餌詳細: {feed_counts}")

        now = datetime.datetime.utcnow()
        last_change_str = data.get("last_image_change", "1970-01-01T00:00:00")
        last_change = datetime.datetime.fromisoformat(last_change_str)
        elapsed_seconds = (now - last_change).total_seconds()
        print(f"[check_and_update_evolution] 最終画像変更: {last_change_str} 経過秒数: {elapsed_seconds}")

        if elapsed_seconds < 3600:
            print("[check_and_update_evolution] 画像変更から1時間経過していないためスキップ")
            return

        if total_feed >= EVOLVE_THRESHOLD:
            max_feed_type = None
            max_feed_count = -1
            for kind in EVOLVE_ORDER:
                if feed_counts[kind] > max_feed_count:
                    max_feed_count = feed_counts[kind]
                    max_feed_type = kind
            print(f"[check_and_update_evolution] 進化判定結果: {max_feed_type} (餌数 {max_feed_count})")

            if max_feed_type:
                data["current_image"] = IMAGE_FILES[max_feed_type]
                data["personality"] = PERSONALITY_MAP.get(max_feed_type, "普通")
                for kind in IMAGE_FILES.keys():
                    old_val = data.get(f"feed_{kind}", 0)
                    data[f"feed_{kind}"] = max(0, old_val - EVOLVE_THRESHOLD)
                    print(f"[check_and_update_evolution] feed_{kind}: {old_val} -> {data[f'feed_{kind}']}")
                data["last_image_change"] = now.isoformat()
                save_pet_data(pet_data)
                print("[check_and_update_evolution] 進化完了、データ保存しました")
        else:
            print("[check_and_update_evolution] 餌の総数が閾値未満、進化なし")
    except Exception as e:
        print(f"[check_and_update_evolution] エラー発生: {e}")
        traceback.print_exc()

class PetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pet")
    async def pet(self, ctx):
        try:
            guild_id = str(ctx.guild.id)
            print(f"[petコマンド] 実行 by ギルドID: {guild_id} ユーザー: {ctx.author} ({ctx.author.id})")
            pet_data = load_pet_data()

            if guild_id not in pet_data:
                print("[petコマンド] 新規ギルドデータ作成")
                pet_data[guild_id] = {
                    "current_image": IMAGE_FILES["もちもち"],
                    "personality": "まるまる",
                    "feed_もちもち": 0,
                    "feed_カチカチ": 0,
                    "feed_キラキラ": 0,
                    "feed_ふわふわ": 0,
                    "last_image_change": "1970-01-01T00:00:00"
                }
                save_pet_data(pet_data)

            check_and_update_evolution(pet_data, guild_id)

            data = pet_data[guild_id]

            embed = discord.Embed(title="🐾 ペットの状態", color=discord.Color.green())
            embed.add_field(name="性格", value=data.get("personality", "不明"), inline=False)

            image_file = data.get("current_image", IMAGE_FILES["もちもち"])
            image_path = os.path.join(PET_IMAGES_PATH, image_file)

            if os.path.exists(image_path):
                with open(image_path, "rb") as img:
                    file = discord.File(img, filename=image_file)
                    embed.set_image(url=f"attachment://{image_file}")
                    await ctx.send(embed=embed, file=file)
                    print(f"[petコマンド] 画像送信成功: {image_path}")
            else:
                await ctx.send(embed=embed)
                print(f"[petコマンド] 画像ファイルが存在しません: {image_path}")
        except Exception as e:
            print(f"[petコマンド] エラー発生: {e}")
            traceback.print_exc()
            await ctx.send("❌ エラーが発生しました。管理者に連絡してください。")

def setup(bot):
    bot.add_cog(PetCog(bot))
