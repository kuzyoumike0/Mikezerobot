import discord
from discord.ext import commands

class ExitHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild

        # 特定カテゴリ名を指定する場合
        TARGET_CATEGORY_NAME = "自己紹介"  # 適宜修正してください

        # ギルド内のカテゴリを検索
        category = discord.utils.get(guild.categories, name=TARGET_CATEGORY_NAME)
        if not category:
            print(f"カテゴリ '{TARGET_CATEGORY_NAME}' が見つかりません。")
            return

        # そのカテゴリ内のテキストチャンネルすべてを確認
        for channel in category.text_channels:
            try:
                async for message in channel.history(limit=100):
                    if message.author.id == member.id:
                        await message.delete()
                        print(f"{channel.name} から {member.display_name} のメッセージを削除しました")
            except discord.Forbidden:
                print(f"{channel.name} のメッセージ削除権限がありません")
            except Exception as e:
                print(f"{channel.name} でエラー発生: {e}")

def setup(bot):
    bot.add_cog(ExitHandler(bot))
