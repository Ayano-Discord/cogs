# Future Imports
from __future__ import annotations

# Music Imports
from .akinator import Aki


def setup(bot):
    bot.add_cog(Aki(bot))
