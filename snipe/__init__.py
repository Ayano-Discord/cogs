# Future Imports
from __future__ import annotations

# Music Imports
from .sniper import Sniper

__red_end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users."
)


def setup(bot):
    bot.add_cog(Sniper(bot))
