import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import asyncio
import datetime
import os
import random
from keep_alive import keep_alive

# Keep Aliveを開始（1回だけ）
keep_alive()

# ボットの設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- 変更してください ---
CONFIRM_CHANNEL_ID = 1393019247864713226  # 脱退メンバー検知用チャンネルID
BUMP_CHANNEL_ID = 1389328686192263238     # /bump通知チャンネルID
VC_CHANNEL_ID = 1386201663446057102        # VCチャンネルID
CATEGORY_ID = 1386195396480729159          # 作成先カテゴリID

pending_deletions = {}

# 雑談用のメッセージリスト
chat_messages = [
    "こんにちは！今日はどんな日でしたか？",
    "お疲れ様です！何か面白いことありましたか？",
    "今日も一日お疲れ様でした！",
    "どうもこんにちは！調子はどうですか？",
    "今日は良い天気ですね！",
    "最近どうですか？何かお話聞かせてください",
    "こんにちは！今日も元気ですか？",
    "お疲れ様です！今日は何をしていましたか？",
    "こんにちは！今日は楽しいことありましたか？",
    "どうもお疲れ様です！リラックスしていますか？"
]

@bot.event
async def on_ready():
    print(f"✅ Botログイン完了: {bot.user}")
    print(f'ボット名: {bot.user.name}')
    print(f'ボットID: {bot.user.id}')
    print('------')
    scan_threads.start()
    bump_reminder.start()

@bot.event
async def on_message(message):
    # ボット自身のメッセージは無視
    if message.author == bot.user:
        return

    # 「@雑談　います」というメッセージに反応
    if "暇" in message.content or "暇" in message.content:
        # ランダムに雑談メッセージを選択
        chat_message = random.choice(chat_messages)

        # 少し待ってからメッセージを送信（より自然に見せるため）
        await asyncio.sleep(1)
        await message.channel.send(f"{message.author.mention} {chat_message}")

    # 他のコマンドも処理できるように
    await bot.process_commands(message)

# 脱退ユーザーのスレッド確認（10分おき）
@tasks.loop(minutes=10)
async def scan_threads():
    for guild in bot.guilds:
        for channel in guild.channels:
            if isinstance(channel, discord.ForumChannel):
                for thread in channel.threads:
                    if thread.owner_id and not guild.get_member(thread.owner_id):
                        confirm_channel = guild.get_channel(CONFIRM_CHANNEL_ID)
                        if confirm_channel:
                            embed = discord.Embed(
                                title="🔍 脱退メンバーのフォーラム投稿を検出",
                                description=f"スレッド: {thread.name}",
                                color=discord.Color.orange()
                            )
                            embed.add_field(name="作成者ID", value=str(thread.owner_id), inline=False)
                            embed.add_field(name="スレッドID", value=str(thread.id), inline=False)
                            embed.add_field(name="確認方法", value="✅で削除、❌でスキップ", inline=False)

                            msg = await confirm_channel.send(embed=embed)
                            await msg.add_reaction("✅")
                            await msg.add_reaction("❌")
                            pending_deletions[msg.id] = thread.id
                            await asyncio.sleep(1)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id not in pending_deletions:
        return
    if str(payload.emoji.name) not in ["✅", "❌"]:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return
    user = guild.get_member(payload.user_id)
    if user is None or user.bot:
        return

    channel = bot.get_channel(payload.channel_id)
    msg = await channel.fetch_message(payload.message_id)
    thread_id = pending_deletions[payload.message_id]
    thread = await guild.fetch_channel(thread_id)

    if payload.emoji.name == "✅":
        await thread.delete(reason="管理者の確認により削除")
        await msg.reply(f"🗑 スレッド {thread.name} を削除しました")
    elif payload.emoji.name == "❌":
        await msg.reply(f"⏹ スレッド {thread.name} はスキップされました")

    del pending_deletions[payload.message_id]

# /bump通知（2時間ごと）
@tasks.loop(hours=2)
async def bump_reminder():
    channel = bot.get_channel(BUMP_CHANNEL_ID)
    if channel:
        await channel.send("📢 /bump の時間です！忘れずにバンプしてください！")

# VC参加者専用チャンネル作成ボタン
class CreatePrivateVCChannelView(View):
    @discord.ui.button(label="VCプライベートチャンネル作成", style=discord.ButtonStyle.green)
    async def create_channel(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        vc_channel = guild.get_channel(VC_CHANNEL_ID)
        category = guild.get_channel(CATEGORY_ID)

        if not vc_channel or not category:
            await interaction.response.send_message("⚠ VCチャンネルまたはカテゴリが見つかりません。", ephemeral=True)
            return

        members = vc_channel.members
        if not members:
            await interaction.response.send_message("⚠ VCに参加しているメンバーがいません。", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        for member in members:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        today = datetime.datetime.now().strftime("vc-%Y-%m-%d")

        channel = await guild.create_text_channel(
            name=today,
            overwrites=overwrites,
            category=category
        )

        await interaction.response.send_message(
            f"✅ チャンネル {channel.mention} を作成しました。", ephemeral=True
        )

@bot.command()
async def setup(ctx):
    """VCプライベートチャンネル作成ボタンを表示"""
    view = CreatePrivateVCChannelView()
    await ctx.send("VC参加メンバーだけのプライベートチャンネルを作成します。下のボタンを押してください。", view=view)

# 雑談コマンド（追加機能）
@bot.command(name='雑談')
async def chat_command(ctx):
    """雑談コマンド"""
    chat_message = random.choice(chat_messages)
    await ctx.send(f"{ctx.author.mention} {chat_message}")

# メッセージを追加するコマンド（管理者用）
@bot.command(name='add_chat')
@commands.has_permissions(administrator=True)
async def add_chat_message(ctx, *, message):
    """雑談メッセージを追加する（管理者のみ）"""
    chat_messages.append(message)
    await ctx.send(f"新しい雑談メッセージを追加しました: {message}")

# 現在の雑談メッセージ数を確認
@bot.command(name='chat_count')
async def chat_count(ctx):
    """登録されている雑談メッセージの数を表示"""
    await ctx.send(f"現在 {len(chat_messages)} 個の雑談メッセージが登録されています")

# ヘルプコマンド
@bot.command(name='help_chat')
async def help_chat(ctx):
    """ボットの使い方を説明"""
    embed = discord.Embed(
        title="雑談ボットの使い方",
        description="このボットは雑談機能を提供します",
        color=0x00ff00
    )
    embed.add_field(
        name="基本機能",
        value="「@雑談　います」とメッセージを送ると、ボットが雑談してくれます",
        inline=False
    )
    embed.add_field(
        name="コマンド",
        value="• `!雑談` - 雑談メッセージを送信\n• `!chat_count` - 登録メッセージ数を表示\n• `!help_chat` - このヘルプを表示",
        inline=False
    )
    await ctx.send(embed=embed)

# エラーハンドリング
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("このコマンドを実行する権限がありません。")
    elif isinstance(error, commands.CommandNotFound):
        pass  # コマンドが見つからない場合は無視
    else:
        print(f"エラーが発生しました: {error}")

# ボットを起動（1回だけ）
bot.run(os.getenv("TOKEN"))