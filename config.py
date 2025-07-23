import os

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

# VCカテゴリID（テキストチャンネル作成用カテゴリ）
VC_CATEGORY_ID = SECRET_CATEGORY_ID

# 特定のロールID（読み取り専用権限を与える用など）
SPECIAL_ROLE_ID = 1396919553413353503

# 管理者・モデレーターのロールID
MOD_ROLE_ID = 1396919553413353503

# creategroupコマンドを許可するテキストチャンネルIDリスト
CREATEGROUP_ALLOWED_CHANNELS = [1385323336699219979, 1386584590289866814]

# 時間帯ごとの入室音ファイル名（プロジェクトルートに配置）
JOIN_SOUNDS = {
    "morning": "join_morning.mp3",   # 05:00 ～ 11:59
    "day":     "join_afternoon.mp3",       # 12:00 ～ 16:59
    "evening": "join_evening.mp3",   # 17:00 ～ 21:59
    "night":   "join_night.mp3",     # 22:00 ～ 04:59
}

# 時間帯ごとの退室音ファイル名
LEAVE_SOUNDS = {
    "morning": "leave_morning.mp3",
    "day":     "leave_afternoon.mp3",
    "evening": "leave_evening.mp3",
    "night":   "leave_night.mp3",
}

# 時間帯の判定用（24時間制：開始時刻、終了時刻）
TIME_RANGES = {
    "morning": (5, 12),
    "day":     (12, 17),
    "evening": (17, 22),
    "night":   (22, 5),
}
