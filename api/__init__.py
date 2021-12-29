# Future Imports
from __future__ import annotations

# Music Imports
from .api import HibikiAPI


def setup(bot):
    cog = HibikiAPI(bot)
    bot.add_cog(cog)
