import discord
from discord.ext import commands
import sounddevice as sd
import numpy as np
import wave
import os
import datetime
import asyncio
from scipy.io.wavfile import write

class VoiceRecorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.input_device = self.detect_input_device()
        self.recording_task = None
        self.is_recording = False
        self.fs = 44100  # サンプルレート
        self.buffer = []

    def detect_input_device(self):
        try:
            devices = sd.query_devices()
            for idx, device in enumerate(devices):
                name = device['name'].lower()
                if "ag" in name and device['max_input_channels'] > 0:
                    print(f"✅ 使用するデバイス: {device['name']} (Index: {idx})")
                    return idx
            default_input = sd.default.device[0]
            print(f"⚠️ AG03などが見つかりません。デフォルト入力デバイスを使用します: {default_input}")
            return default_input
        except Exception as e:
            print(f"❌ 録音デバイスの検出に失敗しました: {e}")
            return None

    def audio_callback(self, indata, frames, time, status):
        if self.is_recording:
            self.buffer.append(indata.copy())

    async def record_loop(self):
        try:
            with sd.InputStream(samplerate=self.fs, channels=1, callback=self.audio_callback, device=self.input_device):
                while self.is_recording:
                    await asyncio.sleep(0.5)
        except Exception as e:
            print(f"❌ 録音ストリームエラー: {e}")

    @commands.command()
    async def joinrec(self, ctx):
        if self.is_recording:
            await ctx.send("⚠️ すでに録音中です。")
            return
        if self.input_device is None:
            await ctx.send("❌ 録音デバイスが見つかりません。")
            return

        self.buffer.clear()
        self.is_recording = True
        self.recording_task = asyncio.create_task(self.record_loop())

        await ctx.send("🔴 録音を開始しました。`!stoprec` で停止できます。")

    @commands.command()
    async def stoprec(self, ctx):
        if not self.is_recording:
            await ctx.send("⚠️ 現在録音していません。")
            return

        self.is_recording = False
        if self.recording_task:
            await self.recording_task
            self.recording_task = None

        # バッファを結合して保存
        try:
            audio_data = np.concatenate(self.buffer, axis=0)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"
            os.makedirs("recordings", exist_ok=True)
            filepath = os.path.join("recordings", filename)

            write(filepath, self.fs, audio_data)
            await ctx.send(f"✅ 録音完了: `{filename}`")

            # Discordにファイル送信
            with open(filepath, "rb") as f:
                await ctx.send(file=discord.File(f, filename))

        except Exception as e:
            await ctx.send(f"❌ 録音ファイルの保存中にエラーが発生しました: {e}")
            print(f"❌ 保存エラー: {e}")

# ... VoiceRecorder クラスの定義のあと

async def setup(bot):
    await bot.add_cog(VoiceRecorder(bot))
