# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
from typing import Tuple
from urllib.parse import quote_plus

# Dependency Imports
from bs4 import BeautifulSoup
import aiohttp

try:
    # Dependency Imports
    from redbot import json
except ImportError:
    import json

# Music Imports
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass


class LyricUtilities(MixinMeta, ABC, metaclass=CompositeMetaClass):
    """Base class to hold all Lyric utility methods"""

    @staticmethod
    async def get_lyrics_string(artist_song: str) -> Tuple[str, str, str, str]:

        searchquery = quote_plus(artist_song)
        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
            async with session.get(
                f"https://google.com/search?q={searchquery}+lyrics"
            ) as resp:
                response_one = await resp.text()
        soup = BeautifulSoup(response_one, "html.parser")
        bouncer = "Our systems have detected unusual traffic from your computer network"
        if bouncer in soup.get_text():
            title_ = ""
            artist_ = ""
            lyrics_ = "Unable to get lyrics right now. Try again later."
            source_ = ""
        else:
            try:
                title_ = soup.find(
                    "span", class_="BNeawe tAd8D AP7Wnd"
                ).get_text()
                artist_ = soup.find_all("span", class_="BNeawe s3v9rd AP7Wnd")[
                    -1
                ].get_text()
                lyrics_ = soup.find_all("div", class_="BNeawe tAd8D AP7Wnd")[
                    -1
                ].get_text()
                source_ = soup.find_all("span", class_="uEec3 AP7Wnd")[
                    -1
                ].get_text()
            except AttributeError:
                title_, artist_, lyrics_, source_ = (
                    "",
                    "",
                    f"Not able to find the lyrics for {artist_song}.",
                    "",
                )
        return title_, artist_, lyrics_, source_
