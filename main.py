import os
import discord
from discord.ext import commands
from config import TOKEN
import asyncio
from keep_alive import keep_alive
from bump_task import BumpNotifier
import traceback

# Intentsをすべて有効化（Botの権限に応じて必要に応じて調整可能）
intents = discord.Intents.all()
# コマンドプレフィックスは「!」に設定し、Botインスタンスを作成
bot = commands.Bot(command_prefix="!", intents=intents)

# ボイスチャットの状態が変化したときに呼ばれるイベントハンドラ
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return  # Botの入退室は無視する
    # ボイスチャットのチャンネル変更をログに出力
    print(f"[VC変化] {member.name}: {before.channel} → {after.channel}")

# Cog（拡張機能）を非同期で順番にロードする関数
async def load_cogs():
    # ロードしたいcogモジュール名のリスト
    cogs = [
        "helpme",              # ヘルプ関連
        "setupvc",             # VCセットアップ関連
        "vote",                # 投票機能
        "creategroup",         # グループ作成
        "vctimer",             # VCタイマー
        "join_sound",          # VC参加音機能
        "setup_secret",        # シークレット設定
        "server_pet_cog_buttons",  # ペット機能（ボタン付き）
    ]
    for cog in cogs:
        try:
            print(f"📂 Loading cog: {cog} ...")
            # cogsフォルダ内の各モジュールを非同期ロード
            await bot.load_extension(f"cogs.{cog}")
            print(f"✅ Loaded cog: {cog}")
        except Exception as e:
            # ロード失敗時はエラーとスタックトレースを表示
            print(f"❌ Failed to load cog {cog}: {e}")
            traceback.print_exc()

# Botが起動して準備完了したときに呼ばれるイベントハンドラ
@bot.event
async def on_ready():
    print(f"[BOT] Logged in as {bot.user} (ID: {bot.user.id})")
    # Botが参加しているギルド名一覧を表示
    print(f"Guilds: {[guild.name for guild in bot.guilds]}")

# メイン処理（asyncio.run()から呼び出される）
async def main():
    # TOKENがセットされているかをデバッグ表示
    print(f"DEBUG: TOKEN is {'set' if TOKEN else 'not set'}")
    if TOKEN is None or TOKEN == "":
        print("⚠️ TOKENが設定されていません。環境変数を確認してください。")
        return

    # Webサーバーを起動し、死活監視用に使用（不要ならコメントアウトしてOK）
    keep_alive()

    # BumpNotifierクラスのインスタンス化（初期化時に内部でタスクを開始する想定）
    bump = BumpNotifier(bot)

    # Botの非同期コンテキストマネージャー内で動作させる
    async with bot:
        await load_cogs()       # Cog群のロード
        await bot.start(TOKEN)  # Discordへの接続を開始

# このファイルが直接実行された場合のみmain()を実行
if __name__ == "__main__":
    asyncio.run(main())
