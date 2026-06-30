import discord
from discord.ext import commands
from discord.ui import View, Button, UserSelect
import json
import os

from config import CATEGORY_ID

PRIVATE_CHANNEL_DATA_PATH = "data/private_channels.json"


def build_view(channel_id: int) -> View:
    """custom_idにchannel_idを埋め込んだボタン・選択メニュー付きViewを作る。
    状態（作成者・参加者）はインスタンスではなくJSONで管理するため、
    Bot再起動後も on_interaction リスナーがそのまま処理を続けられる。
    """
    view = View(timeout=None)
    view.add_item(UserSelect(
        placeholder="招待するユーザーを選択（作成者・管理者のみ操作可）",
        custom_id=f"private_invite:{channel_id}",
        min_values=1,
        max_values=5,
    ))
    view.add_item(Button(
        label="参加する",
        style=discord.ButtonStyle.success,
        custom_id=f"private_join:{channel_id}",
    ))
    view.add_item(Button(
        label="チャンネルを削除",
        style=discord.ButtonStyle.danger,
        custom_id=f"private_delete:{channel_id}",
    ))
    return view


class PrivateChannelCreator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- 永続化 ----------------
    def load_data(self) -> dict:
        if not os.path.exists(PRIVATE_CHANNEL_DATA_PATH):
            return {}
        try:
            with open(PRIVATE_CHANNEL_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def save_data(self, data: dict):
        os.makedirs(os.path.dirname(PRIVATE_CHANNEL_DATA_PATH), exist_ok=True)
        with open(PRIVATE_CHANNEL_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # ---------------- チャンネル作成 ----------------
    @commands.command()
    async def create_private(self, ctx, *, channel_name: str):
        """参加者限定のプライベートチャンネルを作成"""
        guild = ctx.guild
        category = guild.get_channel(CATEGORY_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

        # 作成者・参加者情報をJSONに保存（再起動しても消えない）
        data = self.load_data()
        data[str(channel.id)] = {
            "creator_id": ctx.author.id,
            "participants": [ctx.author.id],
        }
        self.save_data(data)

        view = build_view(channel.id)

        await ctx.send(
            f"✅ プライベートチャンネル **{channel_name}** を作成しました！参加者は下のボタンを押してください。",
            view=view
        )

        await channel.send(f"🔒 このチャンネルは **{ctx.author.display_name}** により作成されました。")
        await channel.send("日程調整後、`!m2m 月日`（例: `!m2m 0630`）を入力してください。")
        await channel.send("チャンネルを削除したい場合は以下のボタンを押してください。", view=view)

    # ---------------- ボタン処理（再起動耐性あり：on_interactionで直接処理） ----------------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id", "")

        if custom_id.startswith("private_join:"):
            await self._handle_join(interaction, custom_id)
        elif custom_id.startswith("private_delete:"):
            await self._handle_delete(interaction, custom_id)
        elif custom_id.startswith("private_invite:"):
            await self._handle_invite(interaction, custom_id)

    async def _handle_join(self, interaction: discord.Interaction, custom_id: str):
        channel_id = int(custom_id.split(":", 1)[1])
        data = self.load_data()
        entry = data.get(str(channel_id))

        if entry is None:
            await interaction.response.send_message("このチャンネルの情報が見つかりません。", ephemeral=True)
            return

        if interaction.user.id in entry["participants"]:
            await interaction.response.send_message("すでに参加済みです。", ephemeral=True)
            return

        channel = interaction.guild.get_channel(channel_id)
        if channel is None:
            await interaction.response.send_message(
                "チャンネルが見つかりません（削除済みの可能性があります）。", ephemeral=True
            )
            return

        entry["participants"].append(interaction.user.id)
        data[str(channel_id)] = entry
        self.save_data(data)

        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"{channel.mention} に参加しました！", ephemeral=True)

    async def _handle_invite(self, interaction: discord.Interaction, custom_id: str):
        channel_id = int(custom_id.split(":", 1)[1])
        data = self.load_data()
        entry = data.get(str(channel_id))

        is_admin = interaction.user.guild_permissions.manage_channels
        is_creator = entry is not None and interaction.user.id == entry.get("creator_id")

        if not (is_admin or is_creator):
            await interaction.response.send_message(
                "招待できるのは作成者または管理者のみです。", ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(channel_id)
        if channel is None:
            await interaction.response.send_message(
                "チャンネルが見つかりません（削除済みの可能性があります）。", ephemeral=True
            )
            return

        if entry is None:
            await interaction.response.send_message("このチャンネルの情報が見つかりません。", ephemeral=True)
            return

        # 選択されたユーザーIDの一覧（UserSelectの選択結果）
        selected_ids = [int(v) for v in interaction.data.get("values", [])]

        invited = []
        already = []
        for uid in selected_ids:
            member = interaction.guild.get_member(uid)
            if member is None:
                continue
            if uid in entry["participants"]:
                already.append(member.display_name)
                continue
            entry["participants"].append(uid)
            await channel.set_permissions(member, read_messages=True, send_messages=True)
            invited.append(member.mention)

        data[str(channel_id)] = entry
        self.save_data(data)

        msg_parts = []
        if invited:
            msg_parts.append(f"✅ 招待しました: {' '.join(invited)}")
        if already:
            msg_parts.append(f"ℹ️ すでに参加済み: {', '.join(already)}")
        if not msg_parts:
            msg_parts.append("対象のユーザーが見つかりませんでした。")

        await interaction.response.send_message("\n".join(msg_parts), ephemeral=True)

        if invited:
            await channel.send(f"👋 {' '.join(invited)} さんが招待されました！")

    async def _handle_delete(self, interaction: discord.Interaction, custom_id: str):
        channel_id = int(custom_id.split(":", 1)[1])
        data = self.load_data()
        entry = data.get(str(channel_id))

        is_admin = interaction.user.guild_permissions.manage_channels
        is_creator = entry is not None and interaction.user.id == entry.get("creator_id")

        if not (is_admin or is_creator):
            await interaction.response.send_message(
                "このチャンネルを削除できるのは作成者または管理者のみです。", ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(channel_id)
        if channel is None:
            await interaction.response.send_message("チャンネルはすでに削除されています。", ephemeral=True)
            return

        if entry is not None:
            data.pop(str(channel_id), None)
            self.save_data(data)

        await channel.delete()
        await interaction.response.send_message("チャンネルを削除しました。", ephemeral=True)


async def setup(bot):
    await bot.add_cog(PrivateChannelCreator(bot))
