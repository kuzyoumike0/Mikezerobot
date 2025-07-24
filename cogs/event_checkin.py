from discord.ext import commands
import discord

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command()
async def set_event(ctx, year, month, day, *, title):
    await ctx.send(f"イベント: {title} 日付: {year}-{month}-{day} で登録されました。")

bot.run("YOUR_BOT_TOKEN")
