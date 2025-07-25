import os
from datetime import datetime

# トークンは環境変数から取得（.envなどに設定）
TOKEN = os.getenv("TOKEN")

# ギルド（サーバー）ID
GUILD_ID = 1384327412946309160

# 各種チャンネルID
EXIT_CONFIRM_CHANNEL_ID = 1392965873261609110
BUMP_CHANNEL_ID = 1389328686192263238

# カテゴリID（テキストチャンネル作成先など）
CATEGORY_ID = 1396282762004135956
SECRET_CATEGORY_ID = 1397686948130459655

# VCコマンド許可テキストチャンネルID
ALLOWED_TEXT_CHANNEL_ID = 1393103534311997541

# VCチャンネルID（複数VC対応）
VC_CHANNEL_IDS = {
    "セッション１": 1386201663446057102,
    "セッション２": 1397684964430184701,
    "セッション３": 1397685082369818881
}

# ペット関連のチャンネルID
PET_HELP_CHANNEL_ID = 1397793018744012880
PET_RANKING_CHANNEL_ID = 1397794425060589692
PET_COMMAND_CHANNEL_ID = 1397723707606171759  # !petコマンドを打てるチャンネルIDに更新

# ペットの一言を投稿するチャンネルID
DAILY_POST_CHANNEL_ID = 1398250949239242752  # ひとことを送るチャンネルIDに更新


# 餌やり回数に応じた称号ロールID
FEED_TITLE_ROLES = {
    10: 1397793352396574720,
    30: 1397793748926201886,
    50: 1397794033236971601,
}

# 匿名相談チャンネルID
ANON_CHANNEL_ID = 1397965805744029706  

# VCカテゴリID（テキストチャンネル作成先）
VC_CATEGORY_ID = SECRET_CATEGORY_ID

# 特定のロールID
SPECIAL_ROLE_ID = 1396919553413353503

# 管理者・モデレーターのロールID
MOD_ROLE_ID = 1385323031047438437

# creategroupコマンドを許可するチャンネルID
CREATEGROUP_ALLOWED_CHANNELS = [1385323336699219979, 1386584590289866814]

# 謎チャンネル
MYSTERY_CHANNEL_ID = 1397863394064994395
MYSTERY_SET_CHANNEL_ID = 1397867367882821793

# 時間帯ごとの音声ファイル名
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

# 時間帯の範囲
TIME_RANGES = {
    "morning": (5, 12),
    "afternoon": (12, 17),
    "evening": (17, 22),
    "night": (22, 5),
}

# ✅ 追加: persistent_views.json の保存先を定義
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)  # ディレクトリが存在しなければ作成
PERSISTENT_VIEWS_PATH = os.path.join(DATA_DIR, "persistent_views.json")

# 🔽 時間帯判定と音声ファイル取得関数
def get_current_period(hour=None):
    """現在の時間帯を判定する関数。"""
    if hour is None:
        hour = datetime.now().hour

    for period, (start, end) in TIME_RANGES.items():
        if start < end:
            if start <= hour < end:
                return period
        else:
            # 例えば night は 22～5時跨ぎなのでこの処理
            if hour >= start or hour < end:
                return period
    return "unknown"

def get_join_sound():
    """現在の時間帯に対応した入室音ファイル名を返す。"""
    period = get_current_period()
    return JOIN_SOUNDS.get(period, None)

def get_leave_sound():
    """現在の時間帯に対応した退室音ファイル名を返す。"""
    period = get_current_period()
    return LEAVE_SOUNDS.get(period, None)
