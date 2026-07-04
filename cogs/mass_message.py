import discord
from discord.ext import commands
import asyncio

# 1チャンネルごとの送信間隔（秒）
INTERVAL_SECONDS = 180  # 3分


class MassMessage(commands.Cog):
    """カテゴリ内の全テキストチャンネルに、3分おきにWebhookで指定メッセージを送るコグ。
    Webhookを使うため、送信者自身の名前・アイコンで送ったように見える。
    コマンド: !mm カテゴリID メッセージ
    """

    def __init__(self, bot):
        self.bot = bot
        # 実行中のタスクを管理（重複実行防止用）
        self._running_tasks: dict[int, asyncio.Task] = {}

    @commands.command(name="mm")
    @commands.has_permissions(administrator=True)
    async def mass_message(self, ctx, category_id: int, *, message: str):
        """
        指定したカテゴリの全テキストチャンネルに、3分おきにWebhookで
        コマンド実行者の名前・アイコンでメッセージを送る（管理者のみ）。
        使い方: !mm 123456789012345678 お知らせ内容
        """
        guild = ctx.guild
        category = guild.get_channel(category_id)

        if category is None or not isinstance(category, discord.CategoryChannel):
            await ctx.send("指定されたカテゴリが見つかりません。IDを確認してください。")
            return

        text_channels = category.text_channels
        if not text_channels:
            await ctx.send(f"カテゴリ『{category.name}』にテキストチャンネルがありません。")
            return

        # 既に同カテゴリで実行中なら重複を防ぐ
        if category_id in self._running_tasks and not self._running_tasks[category_id].done():
            await ctx.send(
                f"カテゴリ『{category.name}』には現在すでに送信タスクが実行中です。\n"
                f"キャンセルするには `!mm_stop {category_id}` を使ってください。"
            )
            return

        author = ctx.author
        total = len(text_channels)
        estimated_minutes = (total - 1) * 3

        await ctx.send(
            f"📨 カテゴリ『{category.name}』の **{total}チャンネル** に送信を開始します。\n"
            f"⏱️ 3分おき・完了まで約 **{estimated_minutes}分** かかります。\n"
            f"💬 メッセージ: {message}"
        )

        task = asyncio.create_task(
            self._send_to_all(ctx, category, text_channels, message, author)
        )
        self._running_tasks[category_id] = task
        task.add_done_callback(lambda t: self._running_tasks.pop(category_id, None))

    async def _send_to_all(
        self,
        ctx: commands.Context,
        category: discord.CategoryChannel,
        channels: list[discord.TextChannel],
        message: str,
        author: discord.Member,
    ):
        """3分おきに各チャンネルへWebhookで送信する"""
        success = 0
        failed = []

        for i, channel in enumerate(channels):
            # 最初のチャンネルは即送信、以降は3分待機
            if i > 0:
                await asyncio.sleep(INTERVAL_SECONDS)

            webhook = None
            try:
                # チャンネルにWebhookを一時作成
                webhook = await channel.create_webhook(name="mm_sender")
                await webhook.send(
                    content=message,
                    username=author.display_name,
                    avatar_url=author.display_avatar.url,
                )
                success += 1
                print(f"[MassMessage] 送信完了: #{channel.name} ({i+1}/{len(channels)})")
            except discord.Forbidden:
                failed.append(channel.mention)
                print(f"[MassMessage] 権限なし: #{channel.name}")
            except discord.HTTPException as e:
                failed.append(channel.mention)
                print(f"[MassMessage] 送信失敗: #{channel.name} - {e}")
            finally:
                # Webhookを必ず削除
                if webhook:
                    try:
                        await webhook.delete()
                    except discord.HTTPException:
                        pass

        # 完了報告
        result = f"✅ カテゴリ『{category.name}』への送信が完了しました。\n成功: {success}/{len(channels)} チャンネル"
        if failed:
            result += f"\n⚠️ 失敗: {', '.join(failed)}"
        await ctx.send(result)

    @commands.command(name="mm_stop")
    @commands.has_permissions(administrator=True)
    async def mm_stop(self, ctx, category_id: int):
        """
        実行中の !mm タスクをキャンセルする（管理者のみ）。
        使い方: !mm_stop 123456789012345678
        """
        task = self._running_tasks.get(category_id)
        if task is None or task.done():
            await ctx.send("指定されたカテゴリで実行中の送信タスクはありません。")
            return
        task.cancel()
        await ctx.send(f"🛑 カテゴリID `{category_id}` の送信タスクをキャンセルしました。")

    @mass_message.error
    async def mass_message_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("このコマンドは管理者のみ使用できます。")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("使い方: `!mm カテゴリID メッセージ`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("カテゴリIDは数字で指定してください。")
        else:
            print(f"[ERROR] mm: {error}")
            await ctx.send("エラーが発生しました。")

    @mm_stop.error
    async def mm_stop_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("このコマンドは管理者のみ使用できます。")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("カテゴリIDは数字で指定してください。")
        else:
            print(f"[ERROR] mm_stop: {error}")
            await ctx.send("エラーが発生しました。")


async def setup(bot):
    await bot.add_cog(MassMessage(bot))
