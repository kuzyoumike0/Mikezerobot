import discord
from discord.ext import commands
from discord.ui import Button, View
import random

# 景品の上限設定（🧻は除外）
PRIZE_LIMITS = {
    "VCでBGM操作権": 1,
    "宣伝権利": 3,
    "再チャレンジ券": 2,
    "他人の名前編集権": 2,
    "管理人部屋閲覧権利": 2
}

# 当選状況を保存（再起動でリセット）
prize_counts = {key: 0 for key in PRIZE_LIMITS}


class OtoshidamaView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OtoshidamaButton())

class OtoshidamaButton(Button):
    def __init__(self):
        super().__init__(label="お年玉ガチャを引く！", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        available_prizes = []

        # 限度に達していない景品を選別
        for prize, limit in PRIZE_LIMITS.items():
            if prize_counts[prize] < limit:
                available_prizes.append(prize)

        # 🧻は無限に出る
        available_prizes.append("🧻 トイレットペーパー1年分")

        # 念のため確認
        if not available_prizes:
            await interaction.response.send_message("🎁 すべての景品が出尽くしました！", ephemeral=True)
            return

        # 抽選
        prize = random.choice(available_prizes)

        if prize != "🧻 トイレットペーパー1年分":
            prize_counts[prize] += 1  # 当選数を加算
            result_text = f"🎯 あなたが引いたのは **{prize}** でした！"
        else:
            result_text = "🎯 あなたが引いたのは...\n" + "🧻" * 100

        await interaction.response.send_message(result_text, ephemeral=True)


class Otoshidama(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="otoshidama")
    async def otoshidama_command(self, ctx):
        """お年玉ガチャを表示"""
        view = OtoshidamaView()
        await ctx.send("🎍 新春お年玉ガチャへようこそ！ボタンを押して運試し！", view=view)


async def setup(bot):
    await bot.add_cog(Otoshidama(bot))
