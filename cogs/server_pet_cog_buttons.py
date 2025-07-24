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

# 性格マッピング
PERSONALITY_MAP = {
    "キラキラ": "キラキラ",
    "カチカチ": "カチカチ",
    "もちもち": "もちもち",
    "ふわふわ": "まるまる"
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
        return

    if total_feed >= EVOLVE_THRESHOLD:
        max_feed_type = None
        max_feed_count = -1
        for kind in EVOLVE_ORDER:
            if feed_counts[kind] > max_feed_count:
                max_feed_count = feed_counts[kind]
                max_feed_type = kind

        if max_feed_type:
            data["current_image"] = IMAGE_FILES[max_feed_type]
            data["personality"] = PERSONALITY_MAP.get(max_feed_type, "普通")
            for kind in IMAGE_FILES.keys():
                data[f"feed_{kind}"] = max(0, data.get(f"feed_{kind}", 0) - EVOLVE_THRESHOLD)
            data["last_image_change"] = now.isoformat()
            save_pet_data(pet_data)

# （以下のコードはそのままですが、check_and_update_evolution に personality 設定を統合したため、
# ActionButton の callback 内にあった personality 設定の重複は削除してOK）

# 必要なら続きのコードをここに追加（全文長いため、既存コードに合わせて分割できます）
