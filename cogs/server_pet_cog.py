class ServerPetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "server_pet_data.json"
        self.pets = {}
        self.load_data()
        self.channel_name = "pet-room"

        # レベル帯ごとの画像URLマッピング（例）
        self.level_images = {
            range(1, 5): "https://example.com/images/pet_level1.png",
            range(5, 10): "https://example.com/images/pet_level2.png",
            range(10, 20): "https://example.com/images/pet_level3.png",
            range(20, 1000): "https://example.com/images/pet_level4.png",
        }

    def get_pet_image(self, level):
        for level_range, url in self.level_images.items():
            if level in level_range:
                return url
        # デフォルト画像
        return "https://example.com/images/pet_default.png"

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

        pet_image_url = self.get_pet_image(pet["level"])
        embed.set_image(url=pet_image_url)

        channel = await self.get_or_create_pet_channel(ctx.guild)
        await channel.send(embed=embed)
        await ctx.send(f"{channel.mention} にペットの状態を表示しました。")
