import discord
from discord.ext import commands
import json
import os

class ServerPetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "server_pet_data.json"
        self.pets = {}
        self.load_data()

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
        guild_id_str = str(guild_id)
        if guild_id_str not in self.pets:
            # サーバー単位の初期ペットデータ
            self.pets[guild_id_str] = {
                "name": "サーバーペット",
                "level": 1,
                "exp": 0,
                "hunger": 50,  # 0〜100
                "happiness": 50,  # 0〜100
            }

    def add_exp(self, guild_id, amount=10):
        guild_id_str = str(guild_id)
        pet = self.pets[guild_id_str]
        pet["exp"] += amount
        while pet["exp"] >= pet["level"] * 100:
            pet["exp"] -= pet["level"] * 100
            pet["level"] += 1

    @commands.group(name="pet", invoke_without_command=True)
    async def pet(self, ctx):
        """サーバーのペットの状態を確認します。"""
        self.ensure_pet(ctx.guild.id)
        pet = self.pets[str(ctx.guild.id)]

        embed = discord.Embed(title=f"サーバー「{ctx.guild.name}」のペット「{pet['name']}」の状態", color=discord.Color.blue())
        embed.add_field(name="レベル", value=pet["level"])
        embed.add_field(name="経験値", value=f"{pet['exp']}/{pet['level'] * 100}")
        embed.add_field(name="空腹度", value=f"{pet['hunger']} / 100")
        embed.add_field(name="幸福度", value=f"{pet['happiness']} / 100")
        await ctx.send(embed=embed)

    @pet.command(name="setname")
    @commands.has_permissions(administrator=True)
    async def pet_setname(self, ctx, *, name: str):
        """ペットの名前を変更します。（管理者のみ）"""
        self.ensure_pet(ctx.guild.id)
        self.pets[str(ctx.guild.id)]["name"] = name
        self.save_data()
        await ctx.send(f"サーバーのペットの名前を「{name}」に変更しました！")

    @pet.command(name="feed")
    async def pet_feed(self, ctx):
        """ペットに餌をあげて空腹度を回復し、経験値を獲得します。"""
        self.ensure_pet(ctx.guild.id)
        pet = self.pets[str(ctx.guild.id)]

        if pet["hunger"] >= 100:
            await ctx.send("ペットはもう満腹です！")
            return

        pet["hunger"] = min(100, pet["hunger"] + 30)
        pet["happiness"] = min(100, pet["happiness"] + 10)
        self.add_exp(ctx.guild.id, 20)
        self.save_data()
        await ctx.send("ペットに餌をあげました！ 空腹度と幸福度が上がり、経験値も獲得しました。")

    @pet.command(name="walk")
    async def pet_walk(self, ctx):
        """ペットと散歩して幸福度と経験値を上げます。"""
        self.ensure_pet(ctx.guild.id)
        pet = self.pets[str(ctx.guild.id)]

        pet["happiness"] = min(100, pet["happiness"] + 20)
        pet["hunger"] = max(0, pet["hunger"] - 15)
        self.add_exp(ctx.guild.id, 30)
        self.save_data()
        await ctx.send("ペットと散歩しました！ 幸福度が上がり、空腹度が少し下がりました。経験値も獲得しました。")

def setup(bot):
    bot.add_cog(ServerPetCog(bot))
