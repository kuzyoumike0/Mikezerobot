
from .server_pet_cog_buttons import PetCog

async def setup(bot):
    await bot.add_cog(PetCog(bot))
