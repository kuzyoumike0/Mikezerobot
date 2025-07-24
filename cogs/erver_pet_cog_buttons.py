import discord
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.group(name="pet", invoke_without_command=True)
async def pet(ctx):
    await ctx.send("ペットコマンドが動作しています！")

bot.run("YOUR_BOT_TOKEN")
