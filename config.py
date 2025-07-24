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
    "会議VC": 1386201663446057102,
    "作戦VC": 1397684964430184701,
    "秘密VC": 1397685082369818881
}

# pet用のコマンド許可チャンネルID（int）
PET_HELP_CHANNEL_ID = 1397793018744012880  # !pet_helpコマンドが許可されるチャンネルID
PET_RANKING_CHANNEL_ID = 1397794425060589692  # !pet_rankingコマンドが許可されるチャンネルID

# 餌やり回数に応じた称号ロールID（例）
FEED_TITLE_ROLES = {
    10: 1397793352396574720,  # 10回
    30: 1397793748926201886,  # 30回
    50: 1397794033236971601,  # 50回
}


# VCカテゴリID（テキストチャンネル作成用カテゴリ）
VC_CATEGORY_ID = SECRET_CATEGORY_ID

# 特定のロールID（読み取り専用権限を与える用など）
SPECIAL_ROLE_ID = 1396919553413353503

# 管理者・モデレーターのロールID
MOD_ROLE_ID = 1385323031047438437

# creategroupコマンドを許可するテキストチャンネルIDリスト
CREATEGROUP_ALLOWED_CHANNELS = [1385323336699219979, 1386584590289866814]

# 時間帯ごとの入室音ファイル名（プロジェクトルートに配置）
JOIN_SOUNDS = {
    "morning": "join_morning.mp3",   # 05:00 ～ 11:59
    "afternoon": "join_afternoon.mp3",  # 12:00 ～ 16:59
    "evening": "join_evening.mp3",   # 17:00 ～ 21:59
    "night": "join_night.mp3",       # 22:00 ～ 04:59
}

# 時間帯ごとの退室音ファイル名
LEAVE_SOUNDS = {
    "morning": "leave_morning.mp3",
    "afternoon": "leave_afternoon.mp3",
    "evening": "leave_evening.mp3",
    "night": "leave_night.mp3",
}

# 時間帯の判定用（24時間制：開始時刻、終了時刻）
TIME_RANGES = {
    "morning": (5, 12),
    "afternoon": (12, 17),
    "evening": (17, 22),
    "night": (22, 5),
}


def get_current_period(hour=None):
    """
    現在の時間帯を判定する関数。
    hourを指定しなければ現在時刻の時間を使用。

    戻り値は 'morning', 'afternoon', 'evening', 'night' のいずれか。
    """
    if hour is None:
        hour = datetime.now().hour

    for period, (start, end) in TIME_RANGES.items():
        if start < end:
            if start <= hour < end:
                return period
        else:
            # 日をまたぐ時間帯（例：22時～5時）
            if hour >= start or hour < end:
                return period
    return "unknown"


def get_join_sound():
    """
    現在の時間帯に対応した入室音ファイル名を返す。
    該当なしなら None を返す。
    """
    period = get_current_period()
    return JOIN_SOUNDS.get(period, None)


def get_leave_sound():
    """
    現在の時間帯に対応した退室音ファイル名を返す。
    該当なしなら None を返す。
    """
    period = get_current_period()
    return LEAVE_SOUNDS.get(period, None)
