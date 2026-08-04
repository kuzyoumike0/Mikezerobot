import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View
import json
import os
import re

from config import TAKUTU_SETS, SPECIAL_ROLE_ID, MOD_ROLE_ID

GM_ROLE_NAME = "GM"
DATA_PATH = "data/takutu_channels.json"
MAX_SECRET_CHANNELS = 20


def find_set(channel_id: int):
    for conf in TAKUTU_SETS:
        if conf["panel_channel_id"] == channel_id:
            return conf
    return None


def is_gm_or_admin(member: discord.Member) -> bool:
    if member.guild_permissions.manage_channels:
        return True
    return discord.utils.get(member.roles, name=GM_ROLE_NAME) is not None


def load_data() -> dict:
    if not os.path.exists(DATA_PATH):
        return {}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_data(data: dict):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def sanitize(name: str) -> str:
    return re.sub(r"\s+", "-", name).strip("-")[:90] or "channel"


def base_overwrites(guild: discord.Guild, creator: discord.Member) -> dict:
    """全チャンネル共通：@everyone非表示、作成者は閲覧可、GM/管理人ロールに編集権のみ付与。"""
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True
        ),
        creator: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        ),
    }
    # view_channel を付けないと一覧に出ず、リネーム等の編集操作ができない。
    editor_perm = discord.PermissionOverwrite(view_channel=True, manage_channels=True)
    gm_role = discord.utils.get(guild.roles, name=GM_ROLE_NAME)
    if gm_role:
        overwrites[gm_role] = editor_perm
    mod_role = guild.get_role(MOD_ROLE_ID)
    if mod_role and mod_role != gm_role:
        overwrites[mod_role] = editor_perm
    return overwrites


def add_viewers(overwrites: dict, members, send: bool = True):
    for member in members:
        overwrites[member] = discord.PermissionOverwrite(
            view_channel=True, send_messages=send, read_message_history=True
        )


def voice_overwrites(guild: discord.Guild, creator: discord.Member, participants, spectator_role):
    """密談VC用：作成者と参加者は通話可、見学ロールは聞き専で参加できる。"""
    overwrites = base_overwrites(guild, creator)
    overwrites[guild.me] = discord.PermissionOverwrite(
        view_channel=True, connect=True, manage_channels=True
    )
    overwrites[creator] = discord.PermissionOverwrite(
        view_channel=True, connect=True, speak=True
    )
    for member in participants:
        overwrites[member] = discord.PermissionOverwrite(
            view_channel=True, connect=True, speak=True
        )
    if spectator_role:
        overwrites[spectator_role] = discord.PermissionOverwrite(
            view_channel=True, connect=True, speak=False
        )
    return overwrites


class SecretCountModal(Modal, title="立卓"):
    count = TextInput(
        label="密談VCの数",
        placeholder="例: 3（0にすると密談VCは作りません）",
        max_length=2,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        value = self.count.value.strip()
        if not value.isdigit() or int(value) > MAX_SECRET_CHANNELS:
            await interaction.response.send_message(
                f"❌ 密談VCの数は 0〜{MAX_SECRET_CHANNELS} の半角数字で入力してください。",
                ephemeral=True,
            )
            return
        await create_table(interaction, int(value))


async def create_table(interaction: discord.Interaction, secret_count: int):
    conf = find_set(interaction.channel.id)
    guild = interaction.guild
    creator = interaction.user

    category = guild.get_channel(conf["category_id"])
    if not isinstance(category, discord.CategoryChannel):
        await interaction.response.send_message(
            f"❌ カテゴリが見つかりません（ID: {conf['category_id']}）。", ephemeral=True
        )
        return

    vc = guild.get_channel(conf["vc_id"])
    if not isinstance(vc, discord.VoiceChannel):
        await interaction.response.send_message(
            f"❌ ボイスチャンネルが見つかりません（ID: {conf['vc_id']}）。", ephemeral=True
        )
        return

    # 作成者がVCにいる場合も参加者に含める（4人なら個別チャンネル4つ）。
    participants = [m for m in vc.members if not m.bot]
    if not participants:
        await interaction.response.send_message(
            f"⚠️ {vc.mention} に誰も入っていません。VCに入ってから押してください。",
            ephemeral=True,
        )
        return

    data = load_data()
    key = str(conf["panel_channel_id"])
    if data.get(key):
        await interaction.response.send_message(
            "⚠️ この卓のチャンネルはすでに作成されています。作り直す場合は先に「削除」を押してください。",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    spectator_role = guild.get_role(SPECIAL_ROLE_ID)
    created = []

    # Discordはカテゴリ内を「テキスト→ボイス」の順に並べるため、
    # 作成順＝表示順になるようテキストを先に、密談VCを最後に作る。
    try:
        # 1. 全体（作成者＋参加者全員）
        overwrites = base_overwrites(guild, creator)
        add_viewers(overwrites, participants)
        created.append(await guild.create_text_channel(
            "全体", category=category, overwrites=overwrites
        ))

        # 2. 参加者ごとの1対1
        for member in participants:
            overwrites = base_overwrites(guild, creator)
            add_viewers(overwrites, [member])
            channel = await guild.create_text_channel(
                sanitize(member.display_name), category=category, overwrites=overwrites
            )
            if member.id == creator.id:
                await channel.send(f"{member.mention} の個別チャンネルです。")
            else:
                await channel.send(f"{member.mention} の個別チャンネルです。")
            created.append(channel)

        # 3. 壁打ち（作成者＋見学ロールのみ／見学ロールも書き込み可）
        overwrites = base_overwrites(guild, creator)
        if spectator_role:
            overwrites[spectator_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )
        created.append(await guild.create_text_channel(
            "壁打ち", category=category, overwrites=overwrites
        ))

        # 4. 密談VC
        for i in range(1, secret_count + 1):
            overwrites = voice_overwrites(guild, creator, participants, spectator_role)
            created.append(await guild.create_voice_channel(
                f"密談{i}", category=category, overwrites=overwrites
            ))

    except discord.Forbidden:
        data[key] = {"creator_id": creator.id, "channel_ids": [c.id for c in created]}
        save_data(data)
        await interaction.followup.send(
            "❌ Botに『チャンネルの管理』権限がありません。作成済みのチャンネルは「削除」ボタンで消せます。",
            ephemeral=True,
        )
        return

    data[key] = {
        "creator_id": creator.id,
        "channel_ids": [c.id for c in created],
    }
    save_data(data)

    await interaction.followup.send(
        f"✅ {len(created)}個のチャンネルを作成しました。\n"
        + "\n".join(c.mention for c in created),
        ephemeral=True,
    )


class TakutuPanel(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="立卓", style=discord.ButtonStyle.success, custom_id="takutu:create")
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        if find_set(interaction.channel.id) is None:
            await interaction.response.send_message(
                "❌ このチャンネルは立卓パネルの対象外です。", ephemeral=True
            )
            return
        if not is_gm_or_admin(interaction.user):
            await interaction.response.send_message(
                "❌ このボタンはGMロールまたは管理者のみ使用できます。", ephemeral=True
            )
            return
        await interaction.response.send_modal(SecretCountModal())

    @discord.ui.button(label="削除", style=discord.ButtonStyle.danger, custom_id="takutu:delete")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        conf = find_set(interaction.channel.id)
        if conf is None:
            await interaction.response.send_message(
                "❌ このチャンネルは立卓パネルの対象外です。", ephemeral=True
            )
            return
        if not is_gm_or_admin(interaction.user):
            await interaction.response.send_message(
                "❌ このボタンはGMロールまたは管理者のみ使用できます。", ephemeral=True
            )
            return

        data = load_data()
        key = str(conf["panel_channel_id"])
        entry = data.get(key)
        if not entry:
            await interaction.response.send_message(
                "削除対象のチャンネルがありません。", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        deleted = 0
        for channel_id in entry["channel_ids"]:
            channel = interaction.guild.get_channel(channel_id)
            if channel is None:
                continue
            try:
                await channel.delete()
                deleted += 1
            except discord.Forbidden:
                pass

        data.pop(key, None)
        save_data(data)

        await interaction.followup.send(
            f"🗑️ {deleted}個のチャンネルを削除しました。", ephemeral=True
        )


class TakutuPanelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TakutuPanel())

    @commands.command(name="setup_takutu")
    async def setup_takutu(self, ctx):
        """立卓パネルを設置する（対象テキストチャンネル内・GM/管理者のみ）"""
        if find_set(ctx.channel.id) is None:
            await ctx.send("このチャンネルには立卓パネルを設置できません。", delete_after=10)
            return
        if not is_gm_or_admin(ctx.author):
            await ctx.send("このコマンドはGMロールまたは管理者のみ使用できます。", delete_after=10)
            return
        await ctx.send(
            "🎲 **立卓パネル**\n"
            "「立卓」でVC参加者用のチャンネル一式を作成し、「削除」でまとめて削除します。",
            view=TakutuPanel(),
        )


async def setup(bot):
    await bot.add_cog(TakutuPanelCog(bot))
