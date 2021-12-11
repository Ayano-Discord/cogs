# Future Imports
from __future__ import annotations

# Music Imports
from .elements import Elements


async def setup(bot):
    cog = Elements(bot)
    bot.add_cog(cog)
