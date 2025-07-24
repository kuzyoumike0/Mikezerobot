import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os

from config import CATEGORY_ID, CREATEGROUP_ALLOWED_CHANNELS, PERSISTENT_VIEWS_PATH


class CreateGroupView(View):
    def __init__(self, channel_name, message=None):
        super().__init__(timeout=None)
        self.channel_name = channel_name
        self.participants = set()
        self.message = message

    @discord.ui.button(label="参加", style=discord.ButtonStyle.primary)
    async def join(self, interaction: discord.Interaction, button: Button):
        user = interaction.user
        self.participants.add(user)
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)
        existing_channel = discord.utils.get(category.text_channels, name=self.channel_name)

        if existing_channel:
            await existing_channel.set_permissions(user, overwrite=discord.PermissionOverwrite(
                read_messages=True, send_messages=True))
            await interaction.response.send_message(
                f"既存チャンネル '{self.channel_name}' に参加しました。", ephemeral=True)
        else:
            await interaction.response.send_message("参加を記録しました。", ephemeral=True)

        if self.message:
            await self.message.edit(
                content=f"「{self.channel_name}」に参加する人はボタンをクリックしてください： 参加者数: {len(self.participants)}",
                view=self)

    @discord.ui.button(label="作成", style=discord.ButtonStyle.success)
    async def create(self, interaction: discord.Interaction, button: Button):
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
            await guild.create_text_channel(self.channel_name, overwrites=overwrites, category=category)
            await interaction.response.send_message(f"チャンネル '{self.channel_name}' を作成しました。", ephemeral=True)


class CreateGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.load_persistent_views())

    @commands.command()
    async def creategroup(self, ctx, *, channel_name: str):
        if ctx.channel.id not in CREATEGROUP_ALLOWED_CHANNELS:
            await ctx.send("このチャンネルではこのコマンドは使えません。")
            return

        view = CreateGroupView(channel_name)
        message = await ctx.send(
            f"「{channel_name}」に参加する人はボタンをクリックしてください： 参加者数: 0", view=view)
        view.message = message

        # 永続ビューに登録
        try:
            with open(PERSISTENT_VIEWS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        if "creategroup" not in data:
            data["creategroup"] = []

        data["creategroup"].append({
            "channel_id": ctx.channel.id,
            "message_id": message.id,
            "channel_name": channel_name
        })

        with open(PERSISTENT_VIEWS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

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
            if channel:
                try:
                    message = await channel.fetch_message(entry["message_id"])
                    view = CreateGroupView(entry["channel_name"], messag_]()
