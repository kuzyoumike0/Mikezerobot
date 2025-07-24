import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from datetime import datetime
import os

DB_PATH = "data/checkin.db"

class Checkin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.init_db()

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
        c.execute('''
            CREATE TABLE IF NOT EXISTS checkouts (
                user_id INTEGER,
                username TEXT,
                date TEXT,
                time TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def get_today():
        return datetime.now().strftime("%Y-%m-%d")

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

    @app_commands.command(name="checkout", description="❌ 今日の退出を記録します")
    async def checkout(self, interaction: discord.Interaction):
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")
        user_id = interaction.user.id
        username = str(interaction.user)

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM checkouts WHERE user_id = ? AND date = ?", (user_id, date))
        if c.fetchone():
            await interaction.response.send_message("🟡 すでにチェックアウト済みです。", ephemeral=True)
        else:
            c.execute("INSERT INTO checkouts VALUES (?, ?, ?, ?)", (user_id, username, date, time))
            conn.commit()
            await interaction.response.send_message(f"❌ {username} さんの退出を記録しました（{time}）")
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

async def setup(bot):
    await bot.add_cog(Checkin(bot))
