import discord
from discord.ext import commands, tasks
import random
from datetime import datetime, timedelta
import pytz

class Pet:
    def __init__(self, name="ミルクシュガー"):
        self.name = name
        self.experience = 0
        self.mood = 50
        self.appearance = "ふわふわ"
        self.food_counts = {"きらきら": 0, "カチカチ": 0, "もちもち": 0, "ふわふわ": 0}

    def feed(self, food_type):
        self.food_counts[food_type] += 1
        self.experience += 10
        if self.experience > 100:
            self.experience = 100
        self.update_mood(5)
        if self.experience == 100:
            self.evolve()

    def evolve(self):
        max_food = max(self.food_counts, key=self.food_counts.get)
        self.appearance = max_food
        self.experience = 0
        self.food_counts = {key: 0 for key in self.food_counts}

    def update_mood(self, amount):
        self.mood = max(0, min(100, self.mood + amount))

    def walk(self):
        self.update_mood(15)

    def petting(self):
        self.update_mood(10)

    def mood_status(self):
        if self.mood <= 30:
            return "悪い"
        elif self.mood <= 70:
            return "普通"
        else:
            return "元気"

    def get_image_url(self):
        base_url = "https://raw.githubusercontent.com/yourusername/yourrepo/main/images/"
        mapping = {
            ("きらきら", "元気"): "kirakira_genki.png",
            ("きらきら", "普通"): "kirakira_futuu.png",
            ("きらきら", "悪い"): "kirakira_warui.png",
            ("カチカチ", "元気"): "kachikachi_genki.png",
            ("カチカチ", "普通"): "kachikachi_futuu.png",
            ("カチカチ", "悪い"): "kachikachi_warui.png",
            ("もちもち", "元気"): "mochimochi_genki.png",
            ("もちもち", "普通"): "mochimochi_futuu.png",
            ("もちもち", "悪い"): "mochimochi_warui.png",
            ("ふわふわ", "元気"): "fuwafuwa_genki.png",
            ("ふわふわ", "普通"): "fuwafuwa_futuu.png",
            ("ふわふわ", "悪い"): "fuwafuwa_warui.png",
        }
        filename = mapping.get((self.appearance, self.mood_status()), "default.png")
        return base_url + filename


class ServerPetCogButtons(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.shared_pet = Pet()
        self.user_timestamps = {}
        self.comment_channels = {}
        self.sent_today = set()
        self.comment_loop.start()

    def cog_unload(self):
        self.comment_loop.cancel()

    def can_perform_action(self, user_id, action):
        now = datetime.utcnow()
        if user_id not in self.user_timestamps:
            self.user_timestamps[user_id] = {}
        last_time = self.user_timestamps[user_id].get(action)
        if last_time is None or now - last_time >= timedelta(hours=1):
            self.user_timestamps[user_id][action] = now
            return True
        return False

    @commands.command()
    async def pet(self, ctx):
        pet = self.shared_pet
        mood = pet.mood_status()
        appearance = pet.appearance
        exp = pet.experience
        image_url = pet.get_image_url()

        embed = discord.Embed(title=f"{pet.name} の状態", color=0x00ffcc)
        embed.add_field(name="機嫌", value=mood)
        embed.add_field(name="外見", value=appearance)
        embed.add_field(name="経験値", value=f"{exp}/100")
        embed.set_image(url=image_url)

        class PetView(discord.ui.View):
            def __init__(self, author_id):
                super().__init__(timeout=120)
                self.author_id = author_id

            async def interaction_check(self, interaction):
                if interaction.user.id != self.author_id:
                    await interaction.response.send_message("これはあなたの操作パネルです。", ephemeral=True)
                    return False
                return True

            @discord.ui.button(label="餌をあげる", style=discord.ButtonStyle.green)
            async def feed_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if not pet_cog.can_perform_action(interaction.user.id, "feed"):
                    await interaction.response.send_message("餌は1時間に1回しかあげられません。", ephemeral=True)
                    return
                food = random.choice(["きらきら", "カチカチ", "もちもち", "ふわふわ"])
                pet.feed(food)
                await interaction.response.send_message(f"{food} の餌をあげました！", ephemeral=True)
                await self.update_pet_message(interaction)

            @discord.ui.button(label="散歩に行く", style=discord.ButtonStyle.primary)
            async def walk_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if not pet_cog.can_perform_action(interaction.user.id, "walk"):
                    await interaction.response.send_message("散歩は1時間に1回しかできません。", ephemeral=True)
                    return
                pet.walk()
                await interaction.response.send_message("ペットと散歩しました！機嫌が少し上がりました。", ephemeral=True)
                await self.update_pet_message(interaction)

            @discord.ui.button(label="撫でる", style=discord.ButtonStyle.secondary)
            async def pet_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if not pet_cog.can_perform_action(interaction.user.id, "pet"):
                    await interaction.response.send_message("撫でるのは1時間に1回までです。", ephemeral=True)
                    return
                pet.petting()
                await interaction.response.send_message("ペットを撫でました！嬉しそうです。", ephemeral=True)
                await self.update_pet_message(interaction)

            async def update_pet_message(self, interaction):
                mood = pet.mood_status()
                appearance = pet.appearance
                exp = pet.experience
                image_url = pet.get_image_url()

                embed = discord.Embed(title=f"{pet.name} の状態", color=0x00ffcc)
                embed.add_field(name="機嫌", value=mood)
                embed.add_field(name="外見", value=appearance)
                embed.add_field(name="経験値", value=f"{exp}/100")
                embed.set_image(url=image_url)

                await interaction.message.edit(embed=embed, view=self)

        pet_cog = self
        view = PetView(ctx.author.id)
        await ctx.send(embed=embed, view=view)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setcommentchannel(self, ctx, channel: discord.TextChannel):
        self.comment_channels[ctx.guild.id] = channel.id
        await ctx.send(f"✅ 一言コメント送信先チャンネルを {channel.mention} に設定しました。")

    @commands.command()
    async def help_pet(self, ctx):
        embed = discord.Embed(title="🐾 ペット育成コマンド一覧", color=0xffcccc)
        embed.add_field(name="!pet", value="ペットの状態確認・操作（餌・散歩・撫でる）ボタンが出ます。", inline=False)
        embed.add_field(name="!setcommentchannel #チャンネル", value="管理者のみ：コメント送信先チャンネルを設定します。", inline=False)
        embed.add_field(name="餌をあげる", value="餌をあげると経験値が10増加します（最大100）。100になると進化します。", inline=False)
        embed.add_field(name="散歩に行く", value="ペットと散歩して機嫌が15上昇。1時間に1回まで。", inline=False)
        embed.add_field(name="撫でる", value="ペットを撫でて機嫌が10上昇。1時間に1回まで。", inline=False)
        embed.set_footer(text="🌸 ペットの機嫌は「元気」「普通」「悪い」の3段階。全員で育てましょう！")
        await ctx.send(embed=embed)

    @tasks.loop(minutes=1)
    async def comment_loop(self):
        JST = pytz.timezone('Asia/Tokyo')
        now = datetime.now(JST)

        # 毎朝10時に一言コメント送信
        if now.hour == 10 and now.minute == 0:
            for guild in self.bot.guilds:
                channel_id = self.comment_channels.get(guild.id)
                if not channel_id:
                   
