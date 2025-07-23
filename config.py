import os

# トークンの読み込み（.envなどから取得することを想定）
TOKEN = os.getenv("TOKEN")

# サーバー（ギルド）およびチャンネル設定
GUILD_ID = 1384327412946309160
EXIT_CONFIRM_CHANNEL_ID = 1392965873261609110
BUMP_CHANNEL_ID = 1389328686192263238
CATEGORY_ID = 1396282762004135956
VCCOMMAND_CHANNEL_ID = 1393103534311997541
VC_CHANNEL_ID = 1388745035285008475  # 常駐させたいVCのIDに置き換えてください
VC_CATEGORY_ID = 1396282762004135956  # テキストチャンネル作成先カテゴリID
MOD_ROLE_ID = 1396919553413353503  # 管理者/モデレーターのロールID
CREATEGROUP_ALLOWED_CHANNELS = [1385323336699219979, 1386584590289866814]
SPECIAL_ROLE_ID = 1396919553413353503  # チャンネル閲覧許可ロールID
ALLOWED_TEXT_CHANNEL_ID = 1393103534311997541  # VCコマンド使用許可チャンネル

# 🔊 時間帯ごとの入室音ファイル（同名ファイルをプロジェクトルートに配置してください）
JOIN_SOUNDS = {
    "morning": "join_morning.mp3",   # 05:00 ～ 11:59
    "day":     "join_day.mp3",       # 12:00 ～ 16:59
    "evening": "join_evening.mp3",   # 17:00 ～ 21:59
    "night":   "join_night.mp3",     # 22:00 ～ 04:59
}

# 🔊 時間帯ごとの退室音ファイル（必要に応じて）
LEAVE_SOUNDS = {
    "morning": "leave_morning.mp3",
    "day":     "leave_day.mp3",
    "evening": "leave_evening.mp3",
    "night":   "leave_night.mp3",
}

# 🔧 時間帯の定義（参照用）
# 24時間制の「開始時刻（含む）」「終了時刻（含まない）」で定義
TIME_RANGES = {
    "morning": (5, 12),   # 5:00 <= 時 < 12:00
    "day":     (12, 17),  # 12:00 <= 時 < 17:00
    "evening": (17, 22),  # 17:00 <= 時 < 22:00
    "night":   (22, 5),   # 22:00 <= 時 or 時 < 5:00（夜～深夜）
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
            # 夜〜深夜帯（例：22時〜5時）の場合
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
