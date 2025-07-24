import discord
from discord.ext import commands
from discord import app_commands
import csv
import io
import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# イベントデータの保持
# event_id: {
#   "datetime": datetimeオブジェクト,
#   "message_id": メッセージID,
#   "channel_id": チャンネルID,
#   "reactions": {emoji: set(user_ids)}
# }
events = {}
event_counter = 0

# 出欠リアクションに使う絵文字例（参加・不参加・未定）
REACTIONS = {
    "✅": "参加",
    "❌": "不参加",
    "❓": "未定"
}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

# イベント登録コマンド (スラッシュコマンド)
@bot.tree.command(name="set_event", description="イベントの日付と時間を設定します (例: 2025-08-01 19:30)")
@app_commands.describe(datetime_str="YYYY-MM-DD HH:MM の形式で入力してください")
async def set_event(interaction: discord.Interaction, datetime_str: str):
    global event_counter

    try:
        event_dt = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
    except ValueError:
        await interaction.response.send_message("日時の形式が正しくありません。YYYY-MM-DD HH:MM の形式で入力してください。", ephemeral=True)
        return

    event_counter += 1
    event_id = event_counter

    # メッセージを送ってリアクションをつける
    channel = interaction.channel
    msg = await channel.send(
        f"【イベントID {event_id}】\nイベント日時: {event_dt.strftime('%Y-%m-%d %H:%M')}\n"
        f"以下の絵文字で出欠をリアクションしてください。\n" +
        "\n".join(f"{emoji}: {desc}" for emoji, desc in REACTIONS.items())
    )

    for emoji in REACTIONS.keys():
        await msg.add_reaction(emoji)

    # イベント情報を保存
    events[event_id] = {
        "datetime": event_dt,
        "message_id": msg.id,
        "channel_id": channel.id,
        "reactions": {emoji: set() for emoji in REACTIONS.keys()}
    }

    await interaction.response.send_message(f"イベントID {event_id} を登録しました。", ephemeral=True)

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # Botのリアクションや他チャンネルは無視
    if payload.user_id == bot.user.id:
        return

    # どのイベントか判定
    for event_id, event_data in events.items():
        if payload.message_id == event_data["message_id"]:
            emoji = str(payload.emoji)
            if emoji in REACTIONS:
                event_data["reactions"][emoji].add(payload.user_id)
            break

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    for event_id, event_data in events.items():
        if payload.message_id == event_data["message_id"]:
            emoji = str(payload.emoji)
            if emoji in REACTIONS:
                event_data["reactions"][emoji].discard(payload.user_id)
            break

@bot.tree.command(name="export_csv", description="イベントの出欠結果をCSVで出力します")
@app_commands.describe(event_id="CSVに出力したいイベントIDを指定してください")
async def export_csv(interaction: discord.Interaction, event_id: int):
    if event_id not in events:
        await interaction.response.send_message("指定されたイベントIDは存在しません。", ephemeral=True)
        return

    event_data = events[event_id]
    channel = bot.get_channel(event_data["channel_id"])
    if channel is None:
        await interaction.response.send_message("イベントのチャンネルが見つかりません。", ephemeral=True)
        return

    # CSV出力準備
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ニックネーム", "出欠"])

    for emoji, user_ids in event_data["reactions"].items():
        for user_id in user_ids:
            member = channel.guild.get_member(user_id)
            name = member.display_name if member else f"ユーザーID:{user_id}"
            writer.writerow([name, REACTIONS[emoji]])

    output.seek(0)
    file = discord.File(fp=io.BytesIO(output.read().encode()), filename=f"event_{event_id}_attendance.csv")

    await interaction.response.send_message(f"イベントID {event_id} の出欠結果CSVです。", file=file, ephemeral=True)

bot.run("YOUR_BOT_TOKEN")
