# cogs/vc_notify.py

import discord
from discord.ext import commands

class VoiceNotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="vcsend")
    async def vcsend(self, ctx, *, message: str):
        """VCにいる全員に同じDMを送信します。"""
        author = ctx.author

        # 実行者がVCにいない場合
        if author.voice is None or author.voice.channel is None:
            await ctx.send("⚠️ あなたは現在ボイスチャンネルに参加していません。")
            return

        voice_channel = author.voice.channel
        members = voice_channel.members

        if not members:
            await ctx.send("⚠️ ボイスチャンネルに他の参加者がいません。")
            return

        sent_count = 0
        failed = []

        for member in members:
            if member.bot:
                continue  # Botはスキップ
            try:
                await member.send(f"📢 {message}")
                sent_count += 1
            except discord.Forbidden:
                failed.append(member.display_name)

        result_msg = f"✅ {sent_count}人にDMを送信しました。"
        if failed:
            result_msg += f"\n⚠️ 送信失敗：{', '.join(failed)}（DM受信拒否など）"
        await ctx.send(result_msg)


# BotにこのCogを追加するための関数
def setup(bot):
    bot.add_cog(VoiceNotify(bot))
