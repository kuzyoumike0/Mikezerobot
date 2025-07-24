intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@commands.command()
async def test(ctx):
    await ctx.send("Botコマンドは動いています！")
