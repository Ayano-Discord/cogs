# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
from typing import Optional
import asyncio
import datetime
import logging
import time

# Dependency Imports
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
import discord

# My Modded Imports
import lavalink

# Music Imports
from ...apis.playlist_interface import delete_playlist, get_playlist, Playlist
from ...audio_logging import debug_exc_log
from ...utils import BOT_SONG_RE, PlaylistScope
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Music.cog.Events.audio")


class AudioEvents(MixinMeta, ABC, metaclass=CompositeMetaClass):
    @commands.Cog.listener()
    async def on_red_audio_track_start(
        self,
        guild: discord.Guild,
        track: lavalink.Track,
        requester: discord.Member,
    ):
        if not (track and guild):
            return

        if await self.bot.cog_disabled_in_guild(self, guild):
            player = lavalink.get_player(guild.id)
            player.store("autoplay_notified", False)
            await player.stop()
            await player.disconnect()
            await self.config_cache.autoplay.set_currently_in_guild(guild)
            return

        track_identifier = track.track_identifier
        if self.playlist_api is not None:
            daily_cache = (
                await self.config_cache.daily_playlist.get_context_value(guild)
            )
            global_daily_playlists = await self.config_cache.daily_global_playlist.get_context_value(
                guild
            )
            today = datetime.date.today()
            midnight = datetime.datetime.combine(
                today, datetime.datetime.min.time()
            )
            today_id = int(time.mktime(today.timetuple()))
            track_json = self.track_to_json(track)
            if daily_cache:
                name = f"Daily playlist - {today}"
                playlist: Optional[Playlist]
                try:
                    playlist = await get_playlist(
                        playlist_api=self.playlist_api,
                        playlist_number=today_id,
                        scope=PlaylistScope.GUILD.value,
                        bot=self.bot,
                        guild=guild,
                        author=self.bot.user,
                    )
                except RuntimeError:
                    playlist = None

                if playlist:
                    tracks_list = playlist.tracks
                    tracks_list.append(track_json)
                    await playlist.edit({"tracks": tracks_list})
                else:
                    playlist = Playlist(
                        bot=self.bot,
                        scope=PlaylistScope.GUILD.value,
                        author=self.bot.user.id,
                        playlist_id=today_id,
                        name=name,
                        playlist_url=None,
                        tracks=[track_json],
                        guild=guild,
                        playlist_api=self.playlist_api,
                    )
                    await playlist.save()
            if global_daily_playlists:
                global_name = f"Global Daily playlist - {today}"
                try:
                    playlist = await get_playlist(
                        playlist_number=today_id,
                        scope=PlaylistScope.GLOBAL.value,
                        bot=self.bot,
                        guild=guild,
                        author=self.bot.user,
                        playlist_api=self.playlist_api,
                    )
                except RuntimeError:
                    playlist = None
                if playlist:
                    tracks_list = playlist.tracks
                    tracks_list.append(track_json)
                    await playlist.edit({"tracks": tracks_list})
                else:
                    playlist = Playlist(
                        bot=self.bot,
                        scope=PlaylistScope.GLOBAL.value,
                        author=self.bot.user.id,
                        playlist_id=today_id,
                        name=global_name,
                        playlist_url=None,
                        tracks=[track_json],
                        guild=guild,
                        playlist_api=self.playlist_api,
                    )
                    await playlist.save()
            too_old = midnight - datetime.timedelta(days=8)
            too_old_id = int(time.mktime(too_old.timetuple()))
            try:
                await delete_playlist(
                    scope=PlaylistScope.GUILD.value,
                    playlist_id=too_old_id,
                    guild=guild,
                    author=self.bot.user,
                    playlist_api=self.playlist_api,
                    bot=self.bot,
                )
            except Exception as err:
                debug_exc_log(
                    log,
                    err,
                    "Failed to delete daily playlist ID: %d",
                    too_old_id,
                )
            try:
                await delete_playlist(
                    scope=PlaylistScope.GLOBAL.value,
                    playlist_id=too_old_id,
                    guild=guild,
                    author=self.bot.user,
                    playlist_api=self.playlist_api,
                    bot=self.bot,
                )
            except Exception as err:
                debug_exc_log(
                    log,
                    err,
                    "Failed to delete global daily playlist ID: %d",
                    too_old_id,
                )
        persist_cache = (
            await self.config_cache.persistent_queue.get_context_value(guild)
        )
        if persist_cache:
            await self.api_interface.persistent_queue_api.played(
                guild_id=guild.id, track_id=track_identifier
            )
        await self.config_cache.currently_playing_name.set_guild(
            guild, set_to=track.title
        )
        auto_lyrics = await self.config_cache.auto_lyrics.get_context_value(
            guild
        )
        if auto_lyrics:
            notify_channel = lavalink.get_player(guild.id).fetch(
                "notify_channel"
            )
            if notify_channel:
                notify_channel = self.bot.get_channel(notify_channel)
                botsong = BOT_SONG_RE.sub("", track.title).strip()
                title, artist, lyrics, source = await self.get_lyrics_string(
                    botsong
                )
                if all([title, artist, lyrics, source]):
                    paged_embeds = []
                    paged_content = [
                        p for p in pagify(lyrics, page_length=900)
                    ]
                    for index, page in enumerate(paged_content, start=1):
                        e = discord.Embed(
                            title=f"{title} by {artist}",
                            description=page,
                            colour=await self.bot.get_embed_color(
                                notify_channel
                            ),
                        )
                        if source:
                            e.set_footer(
                                text=f"Requested by {track.requester} | Source: {source} | Page: {index}/{len(paged_content)}"
                            )
                        paged_embeds.append(e)
                    if paged_embeds:
                        asyncio.create_task(
                            menu(
                                notify_channel,
                                paged_embeds,
                                controls=DEFAULT_CONTROLS,
                                timeout=180.0,
                            )
                        )

    @commands.Cog.listener()
    async def on_red_audio_queue_end(
        self,
        guild: discord.Guild,
        track: lavalink.Track,
        requester: discord.Member,
    ):
        if not (track and guild):
            return
        if self.api_interface is not None and self.playlist_api is not None:
            await self.api_interface.local_cache_api.youtube.clean_up_old_entries()
            await asyncio.sleep(5)
            await self.playlist_api.delete_scheduled()
            await self.api_interface.persistent_queue_api.drop(guild.id)
            await asyncio.sleep(5)
            await self.api_interface.persistent_queue_api.delete_scheduled()
        await self.config_cache.currently_playing_name.set_guild(guild, None)

    @commands.Cog.listener()
    async def on_red_audio_track_enqueue(
        self,
        guild: discord.Guild,
        track: lavalink.Track,
        requester: discord.Member,
    ):
        if not (track and guild):
            return
        persist_cache = (
            await self.config_cache.persistent_queue.get_context_value(guild)
        )
        if persist_cache:
            await self.api_interface.persistent_queue_api.enqueued(
                guild_id=guild.id, room_id=track.extras["vc"], track=track
            )

    @commands.Cog.listener()
    async def on_red_audio_track_end(
        self,
        guild: discord.Guild,
        track: lavalink.Track,
        requester: discord.Member,
    ):
        if not (track and guild):
            return
        if self.api_interface is not None and self.playlist_api is not None:
            await self.api_interface.local_cache_api.youtube.clean_up_old_entries()
            await asyncio.sleep(5)
            await self.playlist_api.delete_scheduled()
            await self.api_interface.persistent_queue_api.drop(guild.id)
            await asyncio.sleep(5)
            await self.api_interface.persistent_queue_api.delete_scheduled()

    @commands.Cog.listener()
    async def on_red_audio_track_auto_play(
        self,
        guild: discord.Guild,
        track: lavalink.Track,
        requester: discord.Member,
        player: lavalink.Player,
    ):
        notify_channel = self.bot.get_channel(player.fetch("notify_channel"))
        has_perms = self._has_notify_perms(notify_channel)
        tries = 0
        while not player._is_playing:
            await asyncio.sleep(0.1)
            if tries > 1000:
                return
            tries += 1

        if (
            notify_channel
            and has_perms
            and not player.fetch("autoplay_notified", False)
        ):
            if (
                len(player.manager.players) < 10
                or not player._last_resume
                and player._last_resume + datetime.timedelta(seconds=60)
                > datetime.datetime.now(tz=datetime.timezone.utc)
            ):
                await self.send_embed_msg(
                    notify_channel, title="Auto Play started."
                )
            player.store("autoplay_notified", True)
