import discord
from discord.ext import commands
import config  # ← 設定ファイルをインポート

class ExitHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # ======== 設定項目（configから取得） ========
        self.TARGET_CATEGORY_ID = config.CATEGORY_ID
        self.TARGET_FORUM_IDS = []  # 必要ならconfigに追加してください
        self.EXIT_LOG_CHANNEL_ID = config.EXIT_CONFIRM_CHANNEL_ID
        # ===========================================

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        nickname = member.display_name
        username = member.name
        user_id = member.id

        print(f"[ExitHandler] メンバーがサーバーを脱退しました。ニックネーム: {nickname}, ユーザー名: {username}")

        # ログチャンネルにニックネームを投稿
        log_channel = guild.get_channel(self.EXIT_LOG_CHANNEL_ID)
        if log_channel and isinstance(log_channel, discord.TextChannel):
            try:
                await log_channel.send(f"👋 **{nickname}** さん（ID: `{user_id}`）がサーバーを退出しました。")
            except Exception as e:
                print(f"[ExitHandler] ログチャンネルへの送信失敗: {e}")
        else:
            print(f"[ExitHandler] ログチャンネル（ID: {self.EXIT_LOG_CHANNEL_ID}）が見つかりませんでした。")

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
                    threads = forum.threads
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

# setup関数を非同期で定義
async def setup(bot):
    await bot.add_cog(ExitHandler(bot))
