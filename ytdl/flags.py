# Future Imports
from __future__ import annotations

# Standard Library Imports
from typing import Optional

# Dependency Imports
from discord.ext import commands


class Search(commands.FlagConverter, case_insensitive=True):
    search: Optional[str] = None
    random: Optional[str]
    hibiki: Optional[str]
