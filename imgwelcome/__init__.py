# Future Imports
from __future__ import annotations

# Music Imports
from .imgwelcome import ImgWelcome


def setup(bot):
    n = ImgWelcome(bot)
    bot.add_cog(n)
