import discord
from discord.ext import commands
import datetime
import pytz

JST = pytz.timezone("Asia/Tokyo")

SOUNDS = {
    "silence": "sounds/silence.mp3",
    "early_morning": "sounds/early_morning.mp3",
    "morning": "sounds/morning.mp3",
    "afternoon": "sounds/afternoon.mp3",
    "night": "sounds/night.mp3"
}

class JoinSound(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_client = None

    @commands.command()
    async def joinvc(self, ctx):
        if ctx.author.voice is None:
            await ctx.send("VCに入ってからコマンドを使ってください。")
            return
        
        channel = ctx.author.voice.channel
        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.move_to(channel)
        else:
            self.voice_client = await channel.connect()
        
        await ctx.send(f"{channel.name} に接続しました。")
        self.play_silence_loop()

    def play_silence_loop(self):
        if not self.voice_client:
            return
        
        source = discord.FFmpegPCMAudio(SOUNDS["silence"])
        self.voice_client.play(source, after=self.silence_loop_callback)

    def silence_loop_callback(self, error):
        if error:
            print(f"Silence loop error: {error}")
            return
        self.play_silence_loop()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not self.voice_client or not self.voice_client.is_connected():
            return

        target_channel = self.voice_client.channel

        if before.channel != target_channel and after.channel == target_channel:
            await self.play_se_for_time()
        elif before.channel == target_channel and after.channel != target_channel:
            await self.play_se_for_time()

    async def play_se_for_time(self):
        if not self.voice_client or not self.voice_client.is_connected():
            return
        
        now = datetime.datetime.now(JST)
        hour = now.hour

        if 4 <= hour <= 9:
            se = SOUNDS["early_morning"]
        elif 10 <= hour <= 12:
            se = SOUNDS["morning"]
        elif 13 <= hour <= 19:
            se = SOUNDS["afternoon"]
        else:
            se = SOUNDS["night"]

        if self.voice_client.is_playing():
            self.voice_client.stop()
        
        source = discord.FFmpegPCMAudio(se)
        self.voice_client.play(source, after=self.after_se_play)

    def after_se_play(self, error):
        if error:
            print(f"SE play error: {error}")
        self.play_silence_loop()

async def setup(bot):
    await bot.add_cog(JoinSound(bot))
