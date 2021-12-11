# Future Imports
from __future__ import annotations

# Music Imports
from .on_connect import on_connect


async def setup(bot):
    cog = on_connect(bot)
    bot.add_cog(cog)
