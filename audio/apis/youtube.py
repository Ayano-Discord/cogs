# Future Imports
from __future__ import annotations

# Standard Library Imports
from pathlib import Path
from typing import Mapping, Optional, TYPE_CHECKING, Union
import logging

# Dependency Imports
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Cog
from redbot.core.i18n import Translator
import aiohttp

# My Modded Imports
import lavalink

# Music Imports
from ..errors import YouTubeApiError

if TYPE_CHECKING:
    # Music Imports
    from .. import Audio

log = logging.getLogger("red.cogs.Audio.api.YouTube")
_ = Translator("Audio", Path(__file__))
SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"


class YouTubeWrapper:
    """Wrapper for the YouTube Data API."""

    def __init__(
        self,
        bot: Red,
        config: Config,
        session: aiohttp.ClientSession,
        cog: Union["Audio", Cog],
    ):
        self.bot = bot
        self.config = config
        self.session = session
        self.api_key: Optional[str] = None
        self._token: Mapping[str, str] = {}
        self.cog = cog

    async def update_token(self, new_token: Mapping[str, str]):
        self._token = new_token

    async def _get_api_key(
        self,
    ) -> str:
        """
        Get the stored youtube token.

        Not used, only kept for compatibility reasons
        """
        if not self._token:
            self._token = await self.bot.get_shared_api_tokens("youtube")
        self.api_key = self._token.get("api_key", "")
        return self.api_key if self.api_key is not None else ""

    async def get_call(
        self, query: str, player: lavalink.Player
    ) -> Optional[str]:
        """
        Call lavalink loadtracks to get the youtube video url.
        """
        loadresults = await player.search_yt(query)
        tracks = loadresults.tracks
        if tracks == ():
            return None
        url = tracks[0].uri
        return url
