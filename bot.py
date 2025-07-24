import os
import discord
from discord.ext import commands
import asyncio

# config.pyでTOKENを環境変数や設定から読み込む想定
from config import TOKEN

# keep_alive.py: Webサーバ起動（死活監視用）
from keep_alive import keep_alive

# bump_task.py: BUMP通知の独立タスククラス
from bump_task import BumpNotifier

# Intentsをすべて有効化（Botの権限によって調整可能）
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# VC入退室の変化をログに出すイベント
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return  # Botの入退室は無視
    print(f"[VC変化] {member.name}: {before.channel} → {after.channel}")

# Cog群を非同期で順にロードする関数
async def load_cogs():
    cogs = [
        "helpme",            # ヘルプ関連のCog
        "setupvc",           # VC関連のセットアップCog
        "vote",              # 投票機能Cog
        "creategroup",       # グループ作成Cog
        "vctimer",           # VCタイマーCog
        "join_sound",        # VC参加音Cog
        "setup_secret",      # シークレット設定Cog
        "server_pet_cog_buttons",  # ペット機能Cog（ボタン付き）
    ]
    for cog in cogs:
        try:
            # cogsフォルダのcogモジュールを非同期で読み込み
            await bot.load_extension(f"cogs.{cog}")
            print(f"✅ Loaded cog: {cog}")
        except Exception as e:
            print(f"❌ Failed to load cog {cog}: {e}")

# Botが起動し準備完了したときに呼ばれるイベント
@bot.event
async def on_ready():
    print(f"[BOT] Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

# メイン処理：asyncio.run()で実行される
async def main():
    # TOKENが設定されていなければ警告を出して終了
    if TOKEN is None or TOKEN == "":
        print("⚠️ TOKENが設定されていません。環境変数を確認してください。")
        return

    keep_alive()  # Webサーバー起動（死活監視用。不要ならコメントアウト）

    # BumpNotifierクラスを初期化。内部でループ処理を開始する想定
    bump = BumpNotifier(bot)

    # Botの非同期コンテキストマネージャー内で動作
    async with bot:
        await load_cogs()       # Cog群をロード
        await bot.start(TOKEN)  # Botを起動しDiscordに接続

# このファイルが直接実行されたときだけmain()を実行する
if __name__ == "__main__":
    asyncio.run(main())
