import discord
from discord.ext import commands
import asyncio
import os
import sounddevice as sd
import wave
import threading
import platform
import subprocess
from datetime import datetime

RECORDINGS_DIR = "recordings"

class Recorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_client = None
        self.is_recording = False
        self.recording_thread = None
        self.audio_filename = None
        self.stop_event = threading.Event()

        # 録音デバイス名を初期化
        self.input_device_name = self.detect_input_device()

    def detect_input_device(self):
        os_type = platform.system()
        devices = sd.query_devices()
        if os_type == "Linux":
            # Linuxでモニターソースを優先検出
            for dev in devices:
                if "monitor" in dev['name'].lower():
                    return dev['name']
        elif os_type == "Windows":
            for dev in devices:
                if "loopback" in dev['name'].lower() or "stereo mix" in dev['name'].lower() or "audio-capturer" in dev['name'].lower():
                    return dev['name']
        # fallback: デフォルトデバイス
        return sd.query_devices(kind='input')['name']

    def record_audio(self, filename):
        samplerate = 44100
        channels = 2
        try:
            device_info = sd.query_devices(self.input_device_name, kind='input')
            samplerate = int(device_info['default_samplerate'])
        except Exception as e:
            print(f"デバイス情報取得エラー: {e}")

        try:
            with sf.SoundFile(filename, mode='x', samplerate=samplerate, channels=channels, subtype='PCM_16') as file:
                with sd.InputStream(samplerate=samplerate, device=self.input_device_name,
                                    channels=channels, callback=lambda indata, frames, time, status: file.write(indata)):
                    print(f"[録音開始] デバイス: {self.input_device_name}")
                    self.stop_event.clear()
                    while not self.stop_event.is_set():
                        sd.sleep(100)
        except Exception as e:
            print(f"[録音エラー] {e}")

    @commands.command(name="joinrec")
    async def joinrec(self, ctx):
        if not ctx.author.voice:
            await ctx.send("❌ ボイスチャンネルに接続してから実行してください。")
            return

        channel = ctx.author.voice.channel
        if ctx.voice_client:
            self.voice_client = ctx.voice_client
        else:
            self.voice_client = await channel.connect()

        if not os.path.exists(RECORDINGS_DIR):
            os.makedirs(RECORDINGS_DIR)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.audio_filename = os.path.join(RECORDINGS_DIR, f"recording_{timestamp}.wav")
        self.is_recording = True
        self.recording_thread = threading.Thread(target=self.record_audio, args=(self.audio_filename,))
        self.recording_thread.start()

        await ctx.send(f"🔴 録音を開始しました。\n🎙 デバイス: `{self.input_device_name}`")

    @commands.command(name="stoprec")
    async def stoprec(self, ctx):
        if not self.is_recording:
            await ctx.send("⚠️ 録音は行われていません。")
            return

        self.stop_event.set()
        self.recording_thread.join()
        self.is_recording = False

        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None

        await ctx.send(f"🛑 録音を停止しました。\n💾 保存ファイル: `{self.audio_filename}`")

    @commands.command(name="helprec")
    async def helprec(self, ctx):
        embed = discord.Embed(title="🎙 Recorder Bot Help", color=discord.Color.green())
        embed.add_field(name="!joinrec", value="VCに参加し録音を開始します。", inline=False)
        embed.add_field(name="!stoprec", value="録音を停止し、ファイルを保存してVCから退出します。", inline=False)
        embed.add_field(name="録音デバイス", value=f"自動検出されたデバイス: `{self.input_device_name}`", inline=False)
        embed.set_footer(text="録音ファイルは recordings フォルダに保存されます。")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Recorder(bot))
