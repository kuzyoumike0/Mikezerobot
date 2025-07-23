import discord
from discord.ext import commands

class ExitHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # ======== 設定項目 ========
        self.TARGET_CATEGORY_ID = 1388730912396804106  # ← テキストチャンネルのカテゴリIDを指定
        self.TARGET_FORUM_IDS = [
            987654321098765432,  # ← フォーラムチャンネル1のID
            876543210987654321,  # ← フォーラムチャンネル2のID（必要に応じて追加）
        ]
        # ===========================

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        print(f"[ExitHandler] メンバー {member.display_name} が脱退しました。メッセージ削除を開始します。")

        # ---- テキストカテゴリ内チャンネルのメッセージ削除 ----
        category = discord.utils.get(guild.categories, id=self.TARGET_CATEGORY_ID)
        if category:
            for channel in category.channels:
                if isinstance(channel, discord.TextChannel):
                    await self.delete_user_messages(channel, member)
        else:
            print(f"[ExitHandler] カテゴリID {self.TARGET_CATEGORY_ID} が見つかりませんでした。")

        # ---- フォーラムチャンネルのスレッド内メッセージ削除 ----
        for forum_id in self.TARGET_FORUM_IDS:
            forum = guild.get_channel(forum_id)
            if forum and isinstance(forum, discord.ForumChannel):
                try:
                    threads = forum.threads  # 非同期呼び出し不要
                    for thread in threads:
                        await self.delete_user_messages(thread, member)
                except Exception as e:
                    print(f"[ExitHandler] フォーラム {forum.name} のスレッド取得エラー: {e}")
            else:
                print(f"[ExitHandler] フォーラムID {forum_id} が見つからないか、フォーラムではありません。")

    async def delete_user_messages(self, channel, member):
        try:
            async for message in channel.history(limit=100):
                if message.author.id == member.id:
                    await message.delete()
                    print(f"[ExitHandler] {channel.name} から {member.display_name} のメッセージを削除しました。")
        except discord.Forbidden:
            print(f"[ExitHandler] 権限不足で {channel.name} のメッセージを削除できません。")
        except discord.HTTPException as http_err:
            print(f"[ExitHandler] {channel.name} の削除時に HTTP エラー: {http_err}")
        except Exception as e:
            print(f"[ExitHandler] {channel.name} で予期しないエラー: {e}")

def setup(bot):
    bot.add_cog(ExitHandler(bot))
