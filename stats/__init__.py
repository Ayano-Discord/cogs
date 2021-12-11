# Future Imports
from __future__ import annotations

# Music Imports
from .main import Stats


async def setup(bot):
    cog = Stats(bot)
    bot.add_cog(cog)
