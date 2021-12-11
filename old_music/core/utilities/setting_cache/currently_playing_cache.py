# Future Imports
from __future__ import annotations

# Standard Library Imports
from typing import Dict, Optional

# Dependency Imports
import discord

# Music Imports
from .abc import CacheBase


class CurrentlyPlayingNameManager(CacheBase):
    __slots__ = (
        "_config",
        "bot",
        "enable_cache",
        "config_cache",
        "_cached_guild",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_guild: Dict[int, str] = {}

    async def get_guild(self, guild: discord.Guild) -> Optional[str]:
        ret: str
        gid: int = guild.id
        if self.enable_cache and gid in self._cached_guild:
            return self._cached_guild[gid]
        else:
            return None

    async def set_guild(
        self, guild: discord.Guild, set_to: Optional[str]
    ) -> None:
        gid: int = guild.id
        if set_to is not None:
            self._cached_guild[gid] = set_to
        else:
            self._cached_guild.pop(gid, None)

    async def get_context_value(self, guild: discord.Guild) -> Optional[str]:
        return await self.get_guild(guild)

    def reset_globals(self) -> None:
        pass
