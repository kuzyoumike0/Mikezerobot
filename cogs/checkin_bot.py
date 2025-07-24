import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from datetime import datetime
import os
import csv
import io

DB_PATH = "data/checkin.db"

class Checkin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.init_db()
        self.export_date = datetime.now().strftime("%Y-%m-%d")  # デフォルト日付

    def init_db(self):
        os.makedirs("data", exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS checkins (
                user_id INTEGER,
                username TEXT,
                date TEXT,
                time TEXT
            )
        ''')
        conn.commit()
        conn.close()

    @app_commands.command(name="checkin", description="✅ 今日の出席を記録します")
    async def checkin(self, interaction: discord.Interaction):
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")
        user_id = interaction.user.id
        username = str(interaction.user)

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM checkins WHERE user_id = ? AND date = ?", (user_id, date))
        if c.fetchone():
            await interaction.response.send_message("🟡 すでにチェックイン済みです。", ephemeral=True)
        else:
            c.execute("INSERT INTO checkins VALUES (?, ?, ?, ?)", (user_id, username, date, time))
            conn.commit()
            await interaction.response.send_message(f"✅ {username} さんの出席を記録しました（{time}）")
        conn.close()

    @app_commands.command(name="checkin_list", description="📋 今日のチェックイン一覧を表示します")
    async def checkin_list(self, interaction: discord.Interaction):
        date = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT username, time FROM checkins WHERE date = ?", (date,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            await interaction.response.send_message("❗本日のチェックイン記録はまだありません。")
            return

        embed = discord.Embed(title=f"✅ {date} のチェックイン一覧", color=discord.Color.green())
        for username, time in rows:
            embed.add_field(name=username, value=f"🕒 {time}", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="checkin_setdate", description="📅 出力対象日を設定します（形式：YYYY-MM-DD）")
    @app_commands.describe(date="出力対象日")
    async def checkin_setdate(self, interaction: discord.Interaction, date: str):
        try:
            datetime.strptime(date, "%Y-%m-%d")
            self.export_date = date
            await interaction.response.send_message(f"📅 出力対象日を `{date}` に設定しました。")
        except ValueError:
            await interaction.response.send_message("❌ 日付の形式が正しくありません。`YYYY-MM-DD` の形式で指定してください。", ephemeral=True)

    @app_commands.command(name="checkin_export", description="📤 設定された日付の出席データをCSVで出力します")
    async def checkin_export(self, interaction: discord.Interaction):
        date = self.export_date

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id, username, time FROM checkins WHERE date = ?", (date,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            await interaction.response.send_message(f"❗ `{date}` のデータは存在しません。", ephemeral=True)
            return

        # CSV作成
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["User ID", "Username", "Check-in Time"])
        for row in rows:
            writer.writerow(row)

        output.seek(0)
        file = discord.File(fp=io.BytesIO(output.getvalue().encode()), filename=f"checkin_{date}.csv")

        await interaction.response.send_message(
            content=f"✅ `{date}` の出席データをCSVで出力しました：",
            file=file
        )

async def setup(bot):
    await bot.add_cog(Checkin(bot))
