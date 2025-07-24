import os
import discord
from discord.ext import commands
import asyncio

# 環境変数や設定ファイル（config.py）からTOKENを読み込み
try:
    from config import TOKEN
except ImportError:
    print("❌ config.py が見つかりません。TOKENの取得ができません。")
    TOKEN = None

# 死活監視用のFlaskサーバなどがある場合に起動
try:
    from keep_alive import keep_alive
except ImportError:
    print("⚠️ keep_alive.py が見つかりません。死活監視をスキップします。")
    def keep_alive():
        pass  # ダミー定義（Railwayなどで使わないなら空関数でOK）

# BUMP通知用の非同期処理クラス
try:
    from bump_task import BumpNotifier
except ImportError:
    print("⚠️ bump_task.py が見つかりません。BUMP通知をスキップします。")
    class BumpNotifier:
        def __init__(self, bot):
            pass

# Botの権限意図を細かく制御するIntents
intents = discord.Intents.all()  # すべて有効（必要に応じて絞ること）

# Bot本体の生成。接頭辞は ! だが、スラッシュコマンドとの併用も可能
bot = commands.Bot(command_prefix="!", intents=intents)


# ✅ VC入退室をログに出すイベント（確認用）
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return  # Botの入退室はログ対象外
    print(f"[🎙️ VC変化] {member.display_name}: {before.channel} → {after.channel}")


# ✅ 拡張機能（Cog）のロード処理
async def load_cogs():
    cogs = [
        "helpme",                  # ヘルプ
        "setupvc",                 # VC自動作成
        "vote",                    # 投票機能
        "creategroup",             # グループ管理
        "vctimer",                 # VCタイマー
        "join_sound",              # VC参加音
        "setup_secret",            # シークレット設定
        "server_pet_cog_buttons",  # 🐾ペット機能（ボタン付き）
    ]

    for cog in cogs:
        try:
            await bot.load_extension(f"cogs.{cog}")
            print(f"✅ Loaded cog: {cog}")
        except Exception as e:
            print(f"❌ Failed to load cog '{cog}': {e}")


# ✅ Botが起動したときの処理
@bot.event
async def on_ready():
    print(f"\n[BOT起動完了] {bot.user} (ID: {bot.user.id})")
    print("準備が完了しました。全てのイベント・Cogが利用可能です。")
    print("-" * 40)


# ✅ メイン関数（asyncio.run()で呼び出される）
async def main():
    if not TOKEN:
        print("❌ TOKENが未設定です。環境変数や config.py を確認してください。")
        return

    keep_alive()  # Flaskなどでの死活監視（Railwayなどで必須）

    # BUMP通知初期化（動作しない場合は警告のみ）
    try:
        bump = BumpNotifier(bot)
    except Exception as e:
        print(f"⚠️ BumpNotifierの初期化に失敗しました: {e}")

    # Bot起動処理（context managerで自動クリーンアップ）
    async with bot:
        await load_cogs()        # 拡張機能読み込み
        await bot.start(TOKEN)   # 実際にBotを起動


# ✅ このスクリプトが直接実行された場合のみ実行
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ 致命的なエラーでBotが起動できませんでした: {e}")
