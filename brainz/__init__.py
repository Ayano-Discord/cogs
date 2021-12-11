# Future Imports
from __future__ import annotations

# Standard Library Imports
import asyncio

# Music Imports
from .brainz import Brainz


def setup(bot):
    cog = Brainz(bot)
    bot.add_cog(cog)
    asyncio.create_task(cog.initialize())
