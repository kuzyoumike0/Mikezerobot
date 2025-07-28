import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
import asyncio

from config import CATEGORY_ID, CREATEGROUP_ALLOWED_CHANNELS, PERSISTENT_VIEWS_PATH


class CreateGroupView(View):
    def __init__(self, channel_name, message=None, participants=None):
        super().__init__(timeout=None)
        self.channel_name = channel_name.lower().replace(" ", "-")
        self.participants = set(participants) if participants else set()
        self.message = message

        join_button = Button(label="参加", style=discord.ButtonStyle.primary)
        join_button.callback = self.join_callback
        self.add_item(join_button)

        create_button = Button(label="作成", style=discord.ButtonStyle.success)
        create_button.callback = self.create_callback
        self.add_item(create_button)

    async def join_callback(self, interaction: discord.Interaction):
        try:
            user = interaction.user
            self.participants.add(user.id)

            guild = interaction.guild
            category = discord.utils.get(guild.categories, id=CATEGORY_ID)
            existing_channel = discord.utils.get(category.text_channels, name=self.channel_name)

            if existing_channel:
                await existing_channel.set_permissions(user, overwrite=discord.PermissionOverwrite(
                    read_messages=True, send_messages=True))
                await interaction.response.send_message(
                    f"既存チャンネル『{self.channel_name}』に参加しました。", ephemeral=True)
            else:
                await interaction.response.send_message("参加を記録しました。", ephemeral=True)

            if self.message:
                await self.message.edit(
                    content=f"「{self.channel_name}」に参加する人はボタンをクリックしてください： 参加者数: {len(self.participants)}",
                    view=self)
        except Exception as e:
            print(f"[ERROR] join_callback内で例外: {e}")
            await interaction.response.send_message("エラーが発生しました。", ephemeral=True)

    async def create_callback(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
            category = discord.utils.get(guild.categories, id=CATEGORY_ID)

            # ✅ 参加者に作成者を追加しない（修正ポイント）
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False)
            }

            members = []
            for user_id in self.participants:
                member = guild.get_member(user_id)
                if member:
                    members.append(member)
                    overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            existing_channel = discord.utils.get(category.text_channels, name=self.channel_name)
            if existing_channel:
                for member in members:
                    await existing_channel.set_permissions(member, overwrite=discord.PermissionOverwrite(
                        read_messages=True, send_messages=True))
                await interaction.response.send_message("既存のチャンネルに参加者を追加しました。", ephemeral=True)
            else:
                new_channel = await guild.create_text_channel(self.channel_name, overwrites=overwrites, category=category)
                await interaction.response.send_message(f"チャンネル『{self.channel_name}』を作成しました。 <#{new_channel.id}>", ephemeral=True)

            await self.save_persistent_views(interaction)
        except Exception as e:
            print(f"[ERROR] create_callback内で例外: {e}")
            await interaction.response.send_message("エラーが発生しました。", ephemeral=True)

    async def save_persistent_views(self, interaction):
        try:
            if os.path.exists(PERSISTENT_VIEWS_PATH):
                with open(PERSISTENT_VIEWS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}

            if "creategroup" not in data:
                data["creategroup"] = []

            updated = False
            for entry in data["creategroup"]:
                if (entry["channel_id"] == interaction.channel.id and
                        entry["message_id"] == self.message.id):
                    entry["participants"] = list(self.participants)
                    updated = True
                    break

            if not updated:
                data["creategroup"].append({
                    "channel_id": interaction.channel.id,
                    "message_id": self.message.id,
                    "channel_name": self.channel_name,
                    "participants": list(self.participants)
                })

            os.makedirs(os.path.dirname(PERSISTENT_VIEWS_PATH), exist_ok=True)
            with open(PERSISTENT_VIEWS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            print("[CreateGroupView] persistent_views.json に参加者情報を更新保存しました。")
        except Exception as e:
            print(f"[ERROR] save_persistent_viewsで例外: {e}")


class CreateGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[CreateGroup] Cog initialized.")

    async def cog_load(self):
        asyncio.create_task(self.load_persistent_views())
        print("[CreateGroup] cog_load により persistent views をロード開始")

    @commands.command()
    async def creategroup(self, ctx, *, channel_name: str):
        print(f"[creategroup] コマンドが呼ばれました。channel_name={channel_name} チャンネルID={ctx.channel.id}")

        if ctx.channel.id not in CREATEGROUP_ALLOWED_CHANNELS:
            await ctx.send("このチャンネルではこのコマンドは使えません。")
            print("[creategroup] コマンド使用不可のチャンネルからの呼び出し。")
            return

        view = CreateGroupView(channel_name)
        message = await ctx.send(
            f"「{view.channel_name}」に参加する人はボタンをクリックしてください： 参加者数: 0", view=view)
        view.message = message

        try:
            if os.path.exists(PERSISTENT_VIEWS_PATH):
                with open(PERSISTENT_VIEWS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except json.JSONDecodeError:
            data = {}

        if "creategroup" not in data:
            data["creategroup"] = []

        data["creategroup"].append({
            "channel_id": ctx.channel.id,
            "message_id": message.id,
            "channel_name": view.channel_name,
            "participants": []
        })

        os.makedirs(os.path.dirname(PERSISTENT_VIEWS_PATH), exist_ok=True)
        with open(PERSISTENT_VIEWS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            print("[creategroup] persistent_views.json に書き込み完了")

    async def load_persistent_views(self):
        await self.bot.wait_until_ready()

        if not os.path.exists(PERSISTENT_VIEWS_PATH):
            return

        try:
            with open(PERSISTENT_VIEWS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return

        entries = data.get("creategroup", [])
        for entry in entries:
            channel = self.bot.get_channel(entry["channel_id"])
            if channel is None:
                continue
            try:
                message = await channel.fetch_message(entry["message_id"])
                participants = entry.get("participants", [])
                view = CreateGroupView(entry["channel_name"], message, participants)
                self.bot.add_view(view)
            except discord.NotFound:
                continue

    @commands.command()
    async def showgroup(self, ctx, *, channel_name: str):
        """
        参加者をニックネーム形式で表示するコマンド
        """
        if not os.path.exists(PERSISTENT_VIEWS_PATH):
            await ctx.send("データが存在しません。")
            return

        try:
            with open(PERSISTENT_VIEWS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            await ctx.send("データの読み込みに失敗しました。")
            return

        entries = data.get("creategroup", [])
        channel_name = channel_name.lower().replace(" ", "-")
        for entry in entries:
            if entry["channel_name"] == channel_name:
                participant_ids = entry.get("participants", [])
                members = []
                for uid in participant_ids:
                    member = ctx.guild.get_member(uid)
                    if member:
                        members.append(member.display_name)
                if members:
                    await ctx.send(f"**「{channel_name}」の参加者一覧：**\n" + "\n".join(f"- {name}" for name in members))
                else:
                    await ctx.send(f"「{channel_name}」の参加者はいません。")
                return

        await ctx.send(f"「{channel_name}」というグループは見つかりませんでした。")

    @commands.command()
    async def testcmd(self, ctx):
        await ctx.send("testcmdが動いています！")


async def setup(bot):
    await bot.add_cog(CreateGroup(bot))
