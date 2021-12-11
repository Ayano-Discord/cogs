# Future Imports
from __future__ import annotations

# Dependency Imports
from redbot.core.bot import Red

# Music Imports
from .core import Audio


def setup(bot: Red):
    cog = Audio(bot)
    bot.add_cog(cog)
    cog.start_up_task()
