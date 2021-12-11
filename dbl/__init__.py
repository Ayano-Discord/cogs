# Future Imports
from __future__ import annotations

# Music Imports
from .dbl import Dbl


async def setup(bot):
    cog = Dbl(bot)
    bot.add_cog(cog)
