import discord
from discord.ext import commands
import json
import os
import datetime

class ServerPetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "server_pet_data.json"
        self.pets = {}
        self.load_data()
        self.channel_name = "pet-room"

        # 餌ごとの効果と画像ファイルパス（例）
        self.feed_effects = {
            "キラキラ": {"hunger": 20, "happiness": 10, "exp": 30},
            "カチカチ": {"hunger": 40, "happiness": 0,  "exp": 15},
            "もちもち": {"hunger": 10, "happiness": 30, "exp": 50},
        }
        self.feed_images = {
            "キラキラ": "images/kirakira.png",
            "カチカチ": "images/kachikachi.png",
            "もちもち": "images/mochimochi.png",
            "default": "images/default.png",
        }

        # 画像更新の制限管理（guild_id:str -> datetime）
        self.last_image_update = {}

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r", encoding="utf-8") as f:
                self.pets = json.load(f)
        else:
            self.pets = {}

        # 画像更新履歴は別ファイルや同ファイルに含めてもよいですが
        # ここは起動時は空にしています
        self.last_image_update = {}

    def save_data(self):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.pets, f, indent=4, ensure_ascii=False)

    def ensure_pet(self, guild_id):
        gid = str(guild_id)
        if gid not in self.pets:
            self.pets[gid] = {
                "name": "サーバーペット",
                "level": 1,
                "exp": 0,
                "hunger": 50,
                "happiness": 50,
                "feed_counts": { "キラキラ": 0, "カチカチ": 0, "もちもち": 0 }
            }

    def add_exp(self, guild_id, amount=10):
        gid = str(guild_id)
        pet = self.pets[gid]
        pet["exp"] += amount
        while pet["exp"] >= pet["level"] * 100:
            pet["exp"] -= pet["level"] * 100
            pet["level"] += 1

    def get_dominant_feed_type(self, guild_id):
        pet = self.pets[str(guild_id)]
        counts = pet.get("feed_counts", {})
        if not counts:
            return "default"
        dominant = max(counts.items(), key=lambda x: x[1])[0]
        if counts[dominant] == 0:
            return "default"
        return dominant

    def can_update_image(self, guild_id):
        gid = str(guild_id)
        now = datetime.datetime.utcnow()
        last = self.last_image_update.get(gid, None)
        if last is None:
            return True
        elapsed = (now - last).total_seconds()
        return elapsed >= 3 * 3600  # 3時間以上

    def update_image_time(self, guild_id):
        self.last_image_update[str(guild_id)] = datetime.datetime.utcnow()

    async def get_or_create_pet_channel(self, guild: discord.Guild):
        existing = discord.utils.get(guild.text_channels, name=self.channel_name)
        if existing:
            return existing

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        channel = await guild.create_text_channel(
            self.channel_name,
            overwrites=overwrites,
            reason="ペット用テキストチャンネル作成"
        )
        return channel

    @commands.group(name="pet", invoke_without_command=True)
    async def pet(self, ctx):
        self.ensure_pet(ctx.guild.id)
        pet = self.pets[str(ctx.guild.id)]

        # 画像の更新判定
        if self.can_update_image(ctx.guild.id):
            dominant_feed = self.get_dominant_feed_type(ctx.guild.id)
            self.update_image_time(ctx.guild.id)
        else:
            # 3時間未満なら前回のdominant_feedを保持 or default
            dominant_feed = getattr(self, f"cached_dominant_feed_{ctx.guild.id}", "default")

        # キャッシュ更新
        setattr(self, f"cached_dominant_feed_{ctx.guild.id}", dominant_feed)

        image_path = self.feed_images.get(dominant_feed, self.feed_images["default"])

        embed = discord.Embed(
            title=f"サーバー「{ctx.guild.name}」のペット「{pet['name']}」の状態",
            color=discord.Color.blue()
        )
        embed.add_field(name="レベル", value=pet["level"])
        embed.add_field(name="経験値", value=f"{pet['exp']}/{pet['level'] * 100}")
        embed.add_field(name="空腹度", value=f"{pet['hunger']} / 100")
        embed.add_field(name="幸福度", value=f"{pet['happiness']} / 100")
        embed.add_field(name="よく食べた餌", value=dominant_feed)

        file = discord.File(image_path, filename="pet.png")
        embed.set_image(url="attachment://pet.png")

        channel = await self.get_or_create_pet_channel(ctx.guild)
        await channel.send(file=file, embed=embed)
        await ctx.send(f"{channel.mention} にペットの状態を表示しました。")

def setup(bot):
    bot.add_cog(ServerPetCog(bot))
