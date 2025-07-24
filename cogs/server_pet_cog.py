import discord
from discord.ext import commands
import os
import json

class ServerPetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "server_pet_data.json"
        self.pets = {}
        self.load_data()
        self.channel_name = "pet-room"

        # レベル帯ごとの画像ファイルパス
        self.level_images = {
            range(1, 5): "images/pet_level1.png",
            range(5, 10): "images/pet_level2.png",
            range(10, 20): "images/pet_level3.png",
            range(20, 1000): "images/pet_level4.png",
        }

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r", encoding="utf-8") as f:
                self.pets = json.load(f)
        else:
            self.pets = {}

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
                "happiness": 50
            }
            self.save_data()

    def get_pet_image_path(self, level):
        for level_range, path in self.level_images.items():
            if level_range.start <= level < level_range.stop:
                return path
        return "images/default.png"  # デフォルト画像

    async def get_or_create_pet_channel(self, guild: discord.Guild):
        channel = discord.utils.get(guild.text_channels, name=self.channel_name)
        if channel is None:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            channel = await guild.create_text_channel(self.channel_name, overwrites=overwrites)
        return channel

    @commands.group(name="pet", invoke_without_command=True)
    async def pet(self, ctx):
        self.ensure_pet(ctx.guild.id)
        pet = self.pets[str(ctx.guild.id)]

        embed = discord.Embed(
            title=f"サーバー「{ctx.guild.name}」のペット「{pet['name']}」の状態",
            color=discord.Color.blue()
        )
        embed.add_field(name="レベル", value=pet["level"])
        embed.add_field(name="経験値", value=f"{pet['exp']}/{pet['level'] * 100}")
        embed.add_field(name="空腹度", value=f"{pet['hunger']} / 100")
        embed.add_field(name="幸福度", value=f"{pet['happiness']} / 100")

        image_path = self.get_pet_image_path(pet["level"])
        filename = os.path.basename(image_path)
        file = discord.File(image_path, filename=filename)
        embed.set_image(url=f"attachment://{filename}")

        channel = await self.get_or_create_pet_channel(ctx.guild)
        await channel.send(embed=embed, file=file)
        await ctx.send(f"{channel.mention} にペットの状態を表示しました。")

def setup(bot):
    bot.add_cog(ServerPetCog(bot))
