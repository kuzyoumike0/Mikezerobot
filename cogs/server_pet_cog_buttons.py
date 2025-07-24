import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import json
import os
import datetime

DATA_FILE = "server_pet_data.json"
IMAGE_FOLDER = "images"  # 画像フォルダ。botからの相対パス

class FeedButton(Button):
    def __init__(self, label: str, style: discord.ButtonStyle, cog):
        super().__init__(label=label, style=style)
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await self.cog.feed_pet(interaction, self.label)

class ServerPetCogButtons(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_name = "pet-room"
        self.pets = {}
        self.load_data()

        # 餌ごとの経験値増加量
        self.feed_exp = {
            "キラキラ": 15,
            "カチカチ": 10,
            "もちもち": 5,
        }

        # 経験値の閾値で画像を変更
        # レベル1: 0-49, レベル2: 50-99, レベル3: 100-149, レベル4: 150+
        self.level_images = [
            (0, 49, "pet_level1.png"),
            (50, 99, "pet_level2.png"),
            (100, 149, "pet_level3.png"),
            (150, 999999, "pet_level4.png"),
        ]

        # ペットの画像変更は3時間ごと
        self.image_change_interval = datetime.timedelta(hours=3)
        # ユーザーの餌やり制限は1時間に1回
        self.feed_cooldown = datetime.timedelta(hours=1)

        # 起動時に定期タスク開始
        self.image_update_task.start()

    def cog_unload(self):
        self.image_update_task.cancel()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                self.pets = json.load(f)
        else:
            self.pets = {}

    def save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.pets, f, indent=4, ensure_ascii=False)

    def ensure_guild_pet(self, guild_id):
        gid = str(guild_id)
        if gid not in self.pets:
            self.pets[gid] = {
                "exp": 0,
                "last_image_change": None,  # ISO文字列
                "last_feed_times": {},  # {user_id: ISO文字列}
                "current_image": "pet_level1.png",
            }
            self.save_data()

    def get_pet_level_image(self, exp):
        for low, high, filename in self.level_images:
            if low <= exp <= high:
                return filename
        return "pet_level1.png"

    async def get_or_create_pet_channel(self, guild: discord.Guild):
        channel = discord.utils.get(guild.text_channels, name=self.channel_name)
        if channel is None:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            channel = await guild.create_text_channel(self.channel_name, overwrites=overwrites)
        return channel

    async def update_pet_message(self, guild: discord.Guild):
        self.ensure_guild_pet(guild.id)
        pet = self.pets[str(guild.id)]

        channel = await self.get_or_create_pet_channel(guild)

        # ペットの画像URL(Discordアップロードではなくbotの画像パス前提)
        image_path = os.path.join(IMAGE_FOLDER, pet["current_image"])
        if not os.path.isfile(image_path):
            # 画像ファイルがない場合は空文字に
            image_path = ""

        embed = discord.Embed(
            title=f"サーバーのペットの状態",
            description=f"経験値: {pet['exp']}",
            color=discord.Color.blue()
        )

        if image_path:
            file = discord.File(image_path, filename=pet["current_image"])
            embed.set_image(url=f"attachment://{pet['current_image']}")
        else:
            file = None

        # 餌ボタンを作成
        view = View(timeout=None)
        for feed_name, exp_gain in self.feed_exp.items():
            style = discord.ButtonStyle.primary
            view.add_item(FeedButton(label=feed_name, style=style, cog=self))

        # 送信済みメッセージがある場合は更新したいが、ここでは毎回送信(工夫可)
        await channel.send(file=file, embed=embed, view=view)

    @tasks.loop(minutes=10)
    async def image_update_task(self):
        now = datetime.datetime.utcnow()
        updated = False
        for guild_id_str in list(self.pets.keys()):
            pet = self.pets[guild_id_str]

            last_change = None
            if pet["last_image_change"]:
                last_change = datetime.datetime.fromisoformat(pet["last_image_change"])

            if (last_change is None) or (now - last_change >= self.image_change_interval):
                # 画像をexpに応じて変更
                new_image = self.get_pet_level_image(pet["exp"])
                if new_image != pet["current_image"]:
                    pet["current_image"] = new_image
                    pet["last_image_change"] = now.isoformat()
                    updated = True

                    # ギルドIDをintにしてギルドオブジェクト取得
                    guild = self.bot.get_guild(int(guild_id_str))
                    if guild:
                        try:
                            await self.update_pet_message(guild)
                        except Exception as e:
                            print(f"[ERROR] ペット画像更新エラー {guild.name}: {e}")

        if updated:
            self.save_data()

    async def feed_pet(self, interaction: discord.Interaction, feed_type: str):
        guild_id_str = str(interaction.guild.id)
        user_id_str = str(interaction.user.id)
        self.ensure_guild_pet(interaction.guild.id)
        pet = self.pets[guild_id_str]

        now = datetime.datetime.utcnow()

        # クールダウンチェック
        last_feed_str = pet["last_feed_times"].get(user_id_str)
        if last_feed_str:
            last_feed = datetime.datetime.fromisoformat(last_feed_str)
            if now - last_feed < self.feed_cooldown:
                remaining = self.feed_cooldown - (now - last_feed)
                await interaction.response.send_message(
                    f"⏳ まだ時間が経っていません。あと {remaining.seconds//60}分 待ってください。", ephemeral=True
                )
                return

        # 餌の経験値追加
        exp_gain = self.feed_exp.get(feed_type, 0)
        pet["exp"] += exp_gain
        pet["last_feed_times"][user_id_str] = now.isoformat()

        # ペットの画像は3時間ごと更新タスクで変わるためここでは変更しない

        self.save_data()

        await interaction.response.send_message(
            f"🍽️ {interaction.user.display_name} さんがペットに「{feed_type}」の餌をあげました！経験値が {exp_gain} 増えました。", ephemeral=True
        )

    @commands.command(name="pet")
    async def pet_status(self, ctx):
        """サーバーのペットの状態をテキストチャンネルに表示する"""
        self.ensure_guild_pet(ctx.guild.id)
        await self.update_pet_message(ctx.guild)

async def setup(bot):
    await bot.add_cog(ServerPetCogButtons(bot))
