import os
from dotenv import load_dotenv

load_dotenv()  # .envファイルを読み込む

# Discord Botのトークンを環境変数から取得
TOKEN = os.getenv("DISCORD_TOKEN")

# VC音声再生用チャンネルID（数字）
VC_CHANNEL_ID = int(os.getenv("VC_CHANNEL_ID", "123456789012345678"))  # デフォルトは適宜書き換えてください

# 入室音のファイルパスを返す関数
def get_join_sound():
    # 実際のファイルパスに合わせて変更してください
    path = "sounds/join.mp3"
    if os.path.isfile(path):
        return path
    return None

# 退室音のファイルパスを返す関数
def get_leave_sound():
    path = "sounds/leave.mp3"
    if os.path.isfile(path):
        return path
    return None
