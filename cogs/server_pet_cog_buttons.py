from discord.ext import commands
import discord

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command()
async def pet(ctx):
    await ctx.send("✅ !pet が正常に動作しています")

bot.run("YOUR_BOT_TOKEN")
