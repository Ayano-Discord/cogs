# Future Imports
from __future__ import annotations

# Standard Library Imports
from typing import MutableMapping, Tuple, TYPE_CHECKING, Union
import logging

# Dependency Imports
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Cog, Context
from redbot.core.utils import AsyncIter
import aiohttp

# Music Imports
from ..errors import AppleMusicFetchError

if TYPE_CHECKING:
    # Music Imports
    from .. import Audio

log = logging.getLogger("red.cogs.Audio.api.AppleMusic")


APPLE_MUSIC_API_BASE_URL = "https://api.kaogurai.xyz/music/applemusic/"


class AppleMusicWrapper:
    """
    Wrapper for the fake Apple Music API.
    """

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
        self.cog = cog

    async def request_playlist_data(
        self, playlist_id: str, country: str = "US"
    ):
        """
        Requests the data for a playlist.
        """
        async with self.session.get(
            APPLE_MUSIC_API_BASE_URL
            + f"playlist/?playlist_id={playlist_id}&country={country}"
        ) as request:
            if request.status == 200:
                return await request.json()
            raise AppleMusicFetchError(
                "This doesn't seem to be a valid Apple Music URL."
            )

    async def request_album_data(self, album_id: str, country: str = "US"):
        """
        Requests the data for an album.
        """
        async with self.session.get(
            APPLE_MUSIC_API_BASE_URL
            + f"album/?album_id={album_id}&country={country}"
        ) as request:
            if request.status == 200:
                return await request.json()
            raise AppleMusicFetchError(
                "This doesn't seem to be a valid Apple Music URL."
            )

    async def request_track_data(
        self, album_id: str, track_id: str, country: str = "US"
    ):
        """
        Requests the data for a track.
        """
        async with self.session.get(
            APPLE_MUSIC_API_BASE_URL
            + f"track/?album_id={album_id}&track_id={track_id}&country={country}"
        ) as request:
            if request.status == 200:
                return await request.json()
            raise AppleMusicFetchError(
                "This doesn't seem to be a valid Apple Music URL."
            )

    async def do_stuff(
        self, url: str, params: MutableMapping
    ) -> MutableMapping:
        """Do the stuff."""
        url = str(url)
        a = url.split("/")
        if "/playlist/" in url:
            try:
                country = a[3]
            except IndexError:
                return
            try:
                playlist_id = a[6]
            except IndexError:
                return
            r = await self.request_playlist_data(playlist_id, country)
            if r is None:
                return
            return r
        elif "?i=" in url:
            try:
                remove_start = url.split("album/")[1]
            except IndexError:
                pass
            try:
                numbers = remove_start.split("/")[1]
            except Exception:
                pass
            try:
                two = numbers.split("?i=")
            except Exception:
                pass
            try:
                if two[0] != two[1]:
                    r = await self.request_track_data(two[0], two[1])
                    if r is None:
                        return
                    return r
            except Exception:
                pass
        elif "/album/" in url:
            try:
                country = a[3]
            except IndexError:
                return
            try:
                album_id = a[6]
            except IndexError:
                return
            r = await self.request_album_data(album_id, country)
            if r is None:
                return
            return r

    async def mirror_spotify_data(self, track_data):
        """Make the apple music data look like Spotify Data"""
        new_data = {"items": []}
        if not track_data:
            return new_data
        if track_data["resultType"] == "playlist":
            async for item in AsyncIter(track_data["tracks"]):
                tti = {
                    "track": {
                        "name": item["trackName"],
                        "artists": [{"name": item["trackArtist"]["name"]}],
                    },
                }
                new_data["items"].append(tti)
            new_data["total"] = len(track_data["tracks"])
        elif track_data["resultType"] == "album":
            async for item in AsyncIter(track_data["tracks"]):
                tti = {
                    "track": {
                        "name": item["trackName"],
                        "artists": [
                            {"name": track_data["albumArtist"]["name"]}
                        ],
                    },
                }
                new_data["items"].append(tti)
                new_data["total"] = len(track_data["tracks"])
        elif track_data["resultType"] == "track":
            tti = {
                "track": {
                    "name": track_data["track"]["trackName"],
                    "artists": [{"name": track_data["albumArtist"]["name"]}],
                },
            }
            new_data["items"].append(tti)
            new_data["total"] = 1

        return new_data

    async def get_apple_music_track_info(
        self, track_data: MutableMapping, ctx: Context
    ) -> Tuple[str, ...]:
        """Extract track info from apple music response."""
        prefer_lyrics = await self.cog.get_lyrics_status(ctx)
        if "items" in track_data.keys():
            track_data = track_data["items"][0]["track"]
        if "name" in track_data.keys():
            track_name = track_data["name"]
            artist_name = track_data["artists"][0]["name"]
        else:
            track_name = track_data["track"]["name"]
            artist_name = track_data["track"]["artists"][0]["name"]
        track_info = f"{track_name} {artist_name}"
        if prefer_lyrics:
            track_info = f"{track_info} lyrics"
        return track_info
