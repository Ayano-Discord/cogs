# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
from typing import Final, Optional, Pattern, TYPE_CHECKING, Union
from urllib.parse import urlparse
import logging
import re

# Dependency Imports
from redbot import VersionInfo
from redbot.core.commands import Context
import discord

# Music Imports
from ...audio_dataclasses import Query
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

if TYPE_CHECKING:

    # Music Imports
    from . import SettingCacheManager
log = logging.getLogger("red.cogs.Music.cog.Utilities.validation")

_RE_YT_LIST_PLAYLIST: Final[Pattern] = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com|youtu\.?be)(/playlist\?).*(list=)(.*)(&|$)"
)
_MIN_SLASH_SUPPORT = VersionInfo.from_json(
    {"major": 999999, "minor": 1, "micro": 0, "releaselevel": "final"}
)


class ValidationUtilities(MixinMeta, ABC, metaclass=CompositeMetaClass):
    def match_url(self, url: str) -> bool:
        try:
            query_url = urlparse(url)
            return all([query_url.scheme, query_url.netloc, query_url.path])
        except Exception:
            return False

    def match_yt_playlist(self, url: str) -> bool:
        return bool(_RE_YT_LIST_PLAYLIST.match(url))

    def is_url_allowed(self, url: str) -> bool:
        valid_tld = [
            "youtube.com",
            "youtu.be",
            "soundcloud.com",
            "bandcamp.com",
            "vimeo.com",
            "twitch.tv",
            "spotify.com",
            "localtracks",
        ]
        query_url = urlparse(url)
        url_domain = ".".join(query_url.netloc.split(".")[-2:])
        if not query_url.netloc:
            url_domain = ".".join(query_url.path.split("/")[0].split(".")[-2:])
        return url_domain in valid_tld

    def is_vc_full(self, channel: discord.VoiceChannel) -> bool:
        return channel.user_limit != 0 and channel.user_limit <= len(
            channel.members
        )

    def can_join_and_speak(self, channel: discord.VoiceChannel) -> bool:
        current_perms = channel.permissions_for(channel.guild.me)
        return current_perms.speak and current_perms.connect

    async def is_query_allowed(
        self,
        cache: SettingCacheManager,
        ctx_or_channel: Optional[Union[Context, discord.TextChannel]],
        query: str,
        query_obj: Query,
    ) -> bool:
        """Checks if the query is allowed in this server or globally."""
        if ctx_or_channel:
            guild = ctx_or_channel.guild
            query = query.lower().strip()
        else:
            guild = None
        if query_obj is not None:
            query = query_obj.lavalink_query.replace(
                "ytsearch:", "youtubesearch"
            ).replace("scsearch:", "soundcloudsearch")

        return await cache.blacklist_whitelist.allowed_by_whitelist_blacklist(
            query, guild=guild
        )

    @staticmethod
    def is_slash_compatible() -> bool:
        try:
            # Dependency Imports
            from dislash import slash_commands  # noqa: F401

            # Music Imports
            from ...__version__ import version_info

            return _MIN_SLASH_SUPPORT <= version_info
        except ImportError:
            return False
