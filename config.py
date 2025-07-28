import os
from datetime import datetime

# ===== トークン・ギルドID =====
TOKEN = os.getenv("TOKEN")  # .env などに設定された Discord Bot トークン
GUILD_ID = 1384327412946309160  # サーバーID

# ===== チャンネルID =====
EXIT_CONFIRM_CHANNEL_ID = 1392965873261609110  # 脱退通知を送信するチャンネル
BUMP_CHANNEL_ID = 1389328686192263238
PET_COMMAND_CHANNEL_ID = 1397723707606171759  # !pet コマンド用
PET_HELP_CHANNEL_ID = 1397793018744012880
PET_RANKING_CHANNEL_ID = 1397794425060589692
DAILY_POST_CHANNEL_ID = 1398250949239242752  # ペットの一言投稿用
ANON_CHANNEL_ID = 1397965805744029706  # 匿名相談用
MYSTERY_CHANNEL_ID = 1397863394064994395
MYSTERY_SET_CHANNEL_ID = 1397867367882821793

# ===== フォーラムチャンネルID（脱退時メッセージ削除対象） =====
EXIT_FORUM_IDS = [
    987654321098765432,  # フォーラムチャンネル1（例）
    876543210987654321,  # フォーラムチャンネル2（例）
]

# ===== カテゴリID =====
CATEGORY_ID = 1396282762004135956  # 脱退時メッセージ削除対象カテゴリ
SECRET_CATEGORY_ID = 1397686948130459655
VC_CATEGORY_ID = SECRET_CATEGORY_ID  # VCチャンネル用カテゴリ

# ===== VC関連 =====
ALLOWED_TEXT_CHANNEL_ID = 1393103534311997541  # VCコマンド許可テキストチャンネル
VC_CHANNEL_IDS = {
    "セッション１": 1386201663446057102,
    "セッション２": 1397684964430184701,
    "セッション３": 1397685082369818881
}

# ===== ペット育成ロール（称号） =====
FEED_TITLE_ROLES = {
    10: 1397793352396574720,  # 見習い餌やり師😺
    30: 1397793748926201886,  # 一人前の餌やり師😸
    50: 1397794033236971601,  # 伝説の餌やり師😻
}

# 経験値に応じて付与するロール（PetView用）
ROLE_TITLE_10 = 1397793352396574720
ROLE_TITLE_30 = 1397793748926201886
ROLE_TITLE_50 = 1397794033236971601

# ===== 権限・ロール関連 =====
SPECIAL_ROLE_ID = 1396919553413353503  # 特定ロール（密談参加者）
MOD_ROLE_ID = 1385323031047438437      # 管理者・モデレーター

# ===== creategroupコマンド許可チャンネル =====
CREATEGROUP_ALLOWED_CHANNELS = [
    1385323336699219979,
    1386584590289866814
]

# ===== VC入退室サウンド関連 =====
JOIN_SOUNDS = {
    "morning": "join_morning.mp3",
    "afternoon": "join_afternoon.mp3",
    "evening": "join_evening.mp3",
    "night": "join_night.mp3",
}

LEAVE_SOUNDS = {
    "morning": "leave_morning.mp3",
    "afternoon": "leave_afternoon.mp3",
    "evening": "leave_evening.mp3",
    "night": "leave_night.mp3",
}

TIME_RANGES = {
    "morning": (5, 12),
    "afternoon": (12, 17),
    "evening": (17, 22),
    "night": (22, 5),
}

# ===== 永続データ保存先 =====
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

PERSISTENT_VIEWS_PATH = os.path.join(DATA_DIR, "persistent_views.json")
