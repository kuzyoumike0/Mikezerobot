import os

# Botトークン（環境変数から取得）
TOKEN = os.getenv("TOKEN")

# サーバー（ギルド）ID
GUILD_ID = 1384327412946309160

# コマンド使用許可テキストチャンネルID
ALLOWED_TEXT_CHANNEL_ID = 1393103534311997541

# VCコマンド許可チャンネルID（ALLOWED_TEXT_CHANNEL_IDと同じなら不要）
VCCOMMAND_CHANNEL_ID = 1393103534311997541

# VC用カテゴリID（密談用テキストチャンネルの親カテゴリ）
VC_CATEGORY_ID = 1397686948130459655

# 密談用テキストチャンネルを作成するカテゴリID（VC_CATEGORY_IDと同じでもOK）
SECRET_CATEGORY_ID = 1397686948130459655

# 管理者・モデレーター等のロールID（権限管理用）
MOD_ROLE_ID = 1396919553413353503

# チャンネル閲覧許可ロールID（特殊ロール：閲覧のみ許可したい場合に使用）
SPECIAL_ROLE_ID = 1396919553413353503

# 参加グループ作成コマンド許可チャンネルIDリスト
CREATEGROUP_ALLOWED_CHANNELS = [1385323336699219979, 1386584590289866814]

# 複数対応VCの名前とチャンネルIDの辞書（例）
VC_CHANNEL_IDS = {
    "会議VC": 1386201663446057102,
    "作戦VC": 1397684964430184701,
    "秘密VC": 1397685082369818881
}

# 時間帯ごとの入室音ファイル名（プロジェクト内に同名ファイルを配置）
JOIN_SOUNDS = {
    "morning": "join_morning.mp3",   # 05:00 ～ 11:59
    "day":     "join_day.mp3",       # 12:00 ～ 16:59
    "evening": "join_evening.mp3",   # 17:00 ～ 21:59
    "night":   "join_night.mp3",     # 22:00 ～ 04:59
}

# 時間帯ごとの退室音ファイル名（必要に応じて）
LEAVE_SOUNDS = {
    "morning": "leave_morning.mp3",
    "day":     "leave_day.mp3",
    "evening": "leave_evening.mp3",
    "night":   "leave_night.mp3",
}

# 時間帯の定義（24時間制の開始時刻と終了時刻）
TIME_RANGES = {
    "morning": (5, 12),    # 5:00 <= 時 < 12:00
    "day":     (12, 17),   # 12:00 <= 時 < 17:00
    "evening": (17, 22),   # 17:00 <= 時 < 22:00
    "night":   (22, 5),    # 22:00 <= 時 or 時 < 5:00
}

def get_current_period(hour=None):
    """
    現在の時間帯を判定する関数。
    hourを指定しなければ現在時刻を使用。

    戻り値は 'morning', 'day', 'evening', 'night' のいずれか。
    """
    from datetime import datetime

    if hour is None:
        hour = datetime.now().hour

    for period, (start, end) in TIME_RANGES.items():
        if start < end:
            if start <= hour < end:
                return period
        else:
            # 夜～深夜帯（22時～5時）
            if hour >= start or hour < end:
                return period
    return "unknown"

def get_join_sound():
    """
    現在の時間帯に対応した入室音ファイル名を返す
    """
    period = get_current_period()
    return JOIN_SOUNDS.get(period, None)

def get_leave_sound():
    """
    現在の時間帯に対応した退室音ファイル名を返す
    """
    period = get_current_period()
    return LEAVE_SOUNDS.get(period, None)
