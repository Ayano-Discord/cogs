# Future Imports
from __future__ import annotations

# Music Imports
from .gacha import Gacha


async def setup(bot):
    bot.add_cog(Gacha(bot))
