import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
import asyncio

from config import CATEGORY_ID, CREATEGROUP_ALLOWED_CHANNELS, PERSISTENT_VIEWS_PATH


class CreateGroupView(View):
    def __init__(self, channel_name, message=None):
        # timeout=None により無制限の永続ビュー
        super().__init__(timeout=None)
        self.channel_name = channel_name.lower().replace(" ", "-")
        self.participants = set()
        self.message = message

        # persistent=True を付けて明示的にボタンを作成し、callbackを登録する
        join_button = Button(label="参加", style=discord.ButtonStyle.primary, persistent=True)
        join_button.callback = self.join_callback
        self.add_item(join_button)

        create_button = Button(label="作成", style=discord.ButtonStyle.success, persistent=True)
        create_button.callback = self.create_callback
        self.add_item(create_button)

    async def join_callback(self, interaction: discord.Interaction):
        user = interaction.user
        self.participants.add(user)
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

    async def create_callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)
        self.participants.add(interaction.user)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }
        for user in self.participants:
            overwrites[user] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        existing_channel = discord.utils.get(category.text_channels, name=self.channel_name)
        if existing_channel:
            for user in self.participants:
                await existing_channel.set_permissions(user, overwrite=discord.PermissionOverwrite(
                    read_messages=True, send_messages=True))
            await interaction.response.send_message("既存のチャンネルに参加者を追加しました。", ephemeral=True)
        else:
            new_channel = await guild.create_text_channel(self.channel_name, overwrites=overwrites, category=category)
            await interaction.response.send_message(f"チャンネル『{self.channel_name}』を作成しました。 <#{new_channel.id}>", ephemeral=True)


class CreateGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[CreateGroup] Cog initialized.")

    async def cog_load(self):
        # Bot起動後に永続ビューの読み込みを非同期開始
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

        # 永続ビュー情報をpersistent_views.jsonに保存
        try:
            with open(PERSISTENT_VIEWS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                print("[creategroup] persistent_views.json 読み込み成功")
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
            print("[creategroup] persistent_views.json が存在しないか壊れているため新規作成")

        if "creategroup" not in data:
            data["creategroup"] = []

        data["creategroup"].append({
            "channel_id": ctx.channel.id,
            "message_id": message.id,
            "channel_name": view.channel_name
        })

        os.makedirs(os.path.dirname(PERSISTENT_VIEWS_PATH), exist_ok=True)
        with open(PERSISTENT_VIEWS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            print("[creategroup] persistent_views.json に書き込み完了")

    async def load_persistent_views(self):
        await self.bot.wait_until_ready()
        print("[load_persistent_views] Bot起動完了。永続ビューをロード開始")

        if not os.path.exists(PERSISTENT_VIEWS_PATH):
            print("[load_persistent_views] persistent_views.json が存在しません。終了。")
            return

        try:
            with open(PERSISTENT_VIEWS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                print("[load_persistent_views] persistent_views.json 読み込み成功")
        except json.JSONDecodeError:
            print("[load_persistent_views] persistent_views.json が壊れています。終了。")
            return

        entries = data.get("creategroup", [])
        for entry in entries:
            channel = self.bot.get_channel(entry["channel_id"])
            if channel is None:
                print(f"[load_persistent_views] チャンネルID {entry['channel_id']} が見つかりません。スキップ")
                continue
            try:
                message = await channel.fetch_message(entry["message_id"])
                view = CreateGroupView(entry["channel_name"], message)
                self.bot.add_view(view)
                print(f"[load_persistent_views] メッセージID {entry['message_id']} のビューを追加しました。")
            except discord.NotFound:
                print(f"[load_persistent_views] メッセージID {entry['message_id']} が見つかりません。スキップ")
                continue

    @commands.command()
    async def testcmd(self, ctx):
        print("[testcmd] コマンドを受け取りました。")
        await ctx.send("testcmdが動いています！")


async def setup(bot):
    await bot.add_cog(CreateGroup(bot))
    print("[setup] CreateGroup Cog を読み込みました。")
