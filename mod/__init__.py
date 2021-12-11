# Future Imports
from __future__ import annotations

# Music Imports
from .mod import Mod


async def setup(bot):
    cog = Mod(bot)
    bot.add_cog(cog)
    await cog.initialize()
