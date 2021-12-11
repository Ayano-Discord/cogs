# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
from operator import attrgetter
from pathlib import Path
from typing import Union
from urllib.parse import urlparse
import asyncio
import contextlib
import datetime
import logging
import math
import os
import tarfile

# Dependency Imports
from redbot.core import bank, commands
from redbot.core.data_manager import cog_data_path
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import (
    box,
    humanize_list,
    humanize_number,
    pagify,
)
from redbot.core.utils.menus import (
    DEFAULT_CONTROLS,
    menu,
    start_adding_reactions,
)
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
import discord

# My Modded Imports
import lavalink

# Music Imports
from ...audio_dataclasses import LocalPath
from ...converters import ScopeParser
from ...errors import MissingGuild, TooManyMatches
from ...manager import get_latest_lavalink_release
from ...utils import CacheLevel, PlaylistScope
from ..abc import MixinMeta
from ..cog_utils import (
    __version__,
    CompositeMetaClass,
    DISABLED,
    DISABLED_TITLE,
    ENABLED,
    ENABLED_TITLE,
    PlaylistConverter,
)

log = logging.getLogger("red.cogs.Music.cog.Commands.audioset")


class AudioSetCommands(MixinMeta, ABC, metaclass=CompositeMetaClass):
    @commands.group(name="audioset")
    @commands.bot_has_permissions(embed_links=True)
    async def command_audioset(self, ctx: commands.Context):
        """Music configuration options."""

    # --------------------------- GLOBAL COMMANDS ----------------------------

    @command_audioset.group(name="global")
    @commands.is_owner()
    async def command_audioset_global(self, ctx: commands.Context):
        """Bot owner controlled configuration options."""

    @command_audioset_global.command(name="volume", aliases=["vol"])
    async def command_audioset_global_volume(
        self, ctx: commands.Context, volume: int
    ):
        """Set the maximum allowed volume to be set by servers."""
        if not 10 < volume < 500:
            await self.send_embed_msg(
                ctx,
                title="Invalid Setting",
                description="Maximum allowed volume has to be between 10% and 500%.",
            )
            return
        await self.config_cache.volume.set_global(volume)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Maximum allowed volume set to: {volume}%.".format(
                volume=volume
            ),
        )

    @command_audioset_global.command(name="dailyqueue")
    async def command_audioset_global_dailyqueue_override(
        self, ctx: commands.Context
    ):
        """Toggle daily queues, if set to disable, it will disable in all servers

        Daily queues creates a playlist for all tracks played today.

        If disabled, servers will not be able to overwrite it.
        """
        daily_playlists = await self.config_cache.daily_playlist.get_global()
        await self.config_cache.daily_playlist.set_global(not daily_playlists)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Global Daily queues: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not daily_playlists
                else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="autolyrics")
    async def command_audioset_global_auto_lyrics(self, ctx: commands.Context):
        """Toggle whether the bot will be auto lyrics are allowed.


        If disabled, servers will not be able to overwrite it.
        """
        auto_lyrics = await self.config_cache.auto_lyrics.get_global()
        await self.config_cache.auto_lyrics.set_global(not auto_lyrics)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Auto Lyrics: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not auto_lyrics
                else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="notify")
    async def command_audioset_global_dailyqueue_notify(
        self, ctx: commands.Context
    ):
        """Toggle track announcement and other bot messages.


        If disabled, servers will not be able to overwrite it.
        """
        daily_playlists = await self.config_cache.daily_playlist.get_global()
        await self.config_cache.daily_playlist.set_global(not daily_playlists)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Global track announcement: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not daily_playlists
                else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="autodeafen")
    async def command_audioset_global_auto_deafen(self, ctx: commands.Context):
        """Toggle whether the bot will be auto deafened upon joining the voice channel.

        If enabled, servers will not be able to override it.
        """
        auto_deafen = await self.config_cache.auto_deafen.get_global()
        await self.config_cache.auto_deafen.set_global(not auto_deafen)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Auto Deafen: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not auto_deafen
                else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(
        name="emptydisconnect", aliases=["emptydc"]
    )
    async def command_audioset_global_emptydisconnect(
        self, ctx: commands.Context, seconds: int
    ):
        """Auto-disconnect from channel when bot is alone in it for x seconds, 0 to disable.

        `[p]audioset global dc` takes precedence over this setting.

        If enabled, servers cannot override / set a lower time in seconds.
        """
        if seconds < 0:
            return await self.send_embed_msg(
                ctx,
                title="Invalid Time",
                description="Seconds can't be less than zero.",
            )
        if 10 > seconds > 0:
            seconds = 10
        if seconds == 0:
            enabled = False
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Global empty disconnect disabled.",
            )
        else:
            enabled = True
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Global empty disconnect timer set to {num_seconds}.".format(
                    num_seconds=self.get_time_string(seconds)
                ),
            )
        await self.config_cache.empty_dc_timer.set_global(seconds)
        await self.config_cache.empty_dc.set_global(enabled)

    @command_audioset_global.command(name="emptypause")
    async def command_audioset_global_emptypause(
        self, ctx: commands.Context, seconds: int
    ):
        """Auto-pause after x seconds when room is empty, 0 to disable.

        If enabled, servers cannot override / set a lower time in seconds.
        """
        if seconds < 0:
            return await self.send_embed_msg(
                ctx,
                title="Invalid Time",
                description="Seconds can't be less than zero.",
            )
        if 10 > seconds > 0:
            seconds = 10
        if seconds == 0:
            enabled = False
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Global empty pause disabled.",
            )
        else:
            enabled = True
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Global empty pause timer set to {num_seconds}.".format(
                    num_seconds=self.get_time_string(seconds)
                ),
            )
        await self.config_cache.empty_pause_timer.set_global(seconds)
        await self.config_cache.empty_pause.set_global(enabled)

    @command_audioset_global.command(name="lyrics")
    async def command_audioset_global_lyrics(self, ctx: commands.Context):
        """Prioritise tracks with lyrics globally.

        If enabled, servers cannot override.
        """
        prefer_lyrics = await self.config_cache.prefer_lyrics.get_global()
        await self.config_cache.prefer_lyrics.set_global(not prefer_lyrics)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Prefer tracks with lyrics globally: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not prefer_lyrics
                else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="disconnect", aliases=["dc"])
    async def command_audioset_global_dc(self, ctx: commands.Context):
        """Toggle the bot auto-disconnecting when done playing.

        This setting takes precedence over `[p]audioset global emptydisconnect`.

        If enabled, servers cannot override.
        """
        disconnect = await self.config_cache.disconnect.get_global()
        msg = ""
        msg += (
            "Global auto-disconnection at queue end: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not disconnect
                else DISABLED_TITLE
            )
        )
        await self.config_cache.disconnect.set_global(not disconnect)

        await self.send_embed_msg(
            ctx, title="Setting Changed", description=msg
        )

    @command_audioset_global.command(name="jukebox")
    async def command_audioset_global_jukebox(
        self, ctx: commands.Context, price: int
    ):
        """Set a price for queueing tracks for non-mods, 0 to disable.

        If set servers can never go below this value and the jukebox will be enabled globally.
        """

        if not await bank.is_global():
            await self.config_cache.jukebox.set_global(False)
            await self.config_cache.jukebox_price.set_global(0)
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description=(
                    "Jukebox Mode: {true_or_false}\n"
                    "Price per command: {cost} {currency}\n"
                    "\n\n**Reason**: You cannot enable this feature if the bank isn't global\n"
                    "Use `[p]bankset toggleglobal` from the "
                    "`Bank` cog to enable a global bank first."
                ).format(
                    true_or_false=ENABLED_TITLE,
                    cost=0,
                    currency=await bank.get_currency_name(ctx.guild),
                ),
            )

        if price < 0:
            return await self.send_embed_msg(
                ctx,
                title="Invalid Price",
                description="Price can't be less than zero.",
            )
        elif price > 2 ** 63 - 1:
            return await self.send_embed_msg(
                ctx,
                title="Invalid Price",
                description="Price can't be greater or equal to than 2^63.",
            )
        elif price == 0:
            jukebox = False
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Global jukebox mode disabled.",
            )
        else:
            jukebox = True
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Global track queueing command price set to {price} {currency}."
                ).format(
                    price=humanize_number(price),
                    currency=await bank.get_currency_name(ctx.guild),
                ),
            )
        await self.config_cache.jukebox_price.set_global(price)
        await self.config_cache.jukebox.set_global(jukebox)

    @command_audioset_global.command(name="maxlength")
    async def command_audioset_global_maxlength(
        self, ctx: commands.Context, seconds: Union[int, str]
    ):
        """Max length of a track to queue in seconds, 0 to disable.

        Accepts seconds or a value formatted like 00:00:00 (`hh:mm:ss`) or 00:00 (`mm:ss`). Invalid input will turn the max length setting off.

        Setting this value means that servers will never be able to bypass it, however they will be allowed to set short lengths.
        """
        if not isinstance(seconds, int):
            seconds = self.time_convert(seconds)
        if seconds < 0:
            return await self.send_embed_msg(
                ctx,
                title="Invalid length",
                description="Length can't be less than zero.",
            )
        if seconds == 0:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Global track max length disabled.",
            )
        else:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Global track max length set to {seconds}.".format(
                    seconds=self.get_time_string(seconds)
                ),
            )
        await self.config_cache.max_track_length.set_global(seconds)

    @command_audioset_global.command(name="maxqueue")
    async def command_audioset_global_maxqueue(
        self, ctx: commands.Context, size: int
    ):
        """Set the maximum size a queue is allowed to be.

        Default is 10,000, servers cannot go over this value, but they can set smaller values.
        """
        if not 10 < size < 20_000:
            return await self.send_embed_msg(
                ctx,
                title="Invalid Queue Size",
                description="Queue size must bet between 10 and {cap}.".format(
                    cap=humanize_number(20_000)
                ),
            )
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Maximum queue size allowed is now {size}.".format(
                size=humanize_number(size)
            ),
        )
        await self.config_cache.max_queue_size.set_global(size)

    @command_audioset_global.command(name="thumbnail")
    async def command_audioset_global_thumbnail(self, ctx: commands.Context):
        """Toggle displaying a thumbnail on audio messages.

        If enabled servers will not be able to override this setting.
        """
        thumbnail = await self.config_cache.thumbnail.get_global()
        await self.config_cache.thumbnail.set_global(not thumbnail)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Global thumbnail display: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not thumbnail
                else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="countrycode")
    async def command_audioset_global_countrycode(
        self, ctx: commands.Context, country: str
    ):
        """Set the country code for Spotify searches.

        This can be override by servers, however it will set the default value for the bot.
        """
        if len(country) != 2:
            return await self.send_embed_msg(
                ctx,
                title="Invalid Country Code",
                description=(
                    "Please use an official [ISO 3166-1 alpha-2]"
                    "(https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code."
                ),
            )
        country = country.upper()
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Global country Code set to {country}.".format(
                country=country
            ),
        )

        await self.config_cache.country_code.set_global(country)

    @command_audioset_global.command(name="persistqueue")
    async def command_audioset_global_persist_queue(
        self, ctx: commands.Context
    ):
        """Toggle persistent queues.

        Persistent queues allows the current queue to be restored when the queue closes.

        If set servers will be able to overwrite this value.
        """
        persist_cache = await self.config_cache.persistent_queue.get_global()
        await self.config_cache.persistent_queue.set_global(not persist_cache)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Global queue persistence: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not persist_cache
                else DISABLED_TITLE
            ),
        )

    @command_audioset_global.group(name="allowlist", aliases=["whitelist"])
    async def command_audioset_global_whitelist(self, ctx: commands.Context):
        """Manages the global keyword allowlist."""

    @command_audioset_global_whitelist.command(name="add")
    async def command_audioset_global_whitelist_add(
        self, ctx: commands.Context, *, keyword: str
    ):
        """Adds a keyword to the allowlist.

        If anything is added to allowlist, it will reject everything else.
        """
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.add_to_whitelist(
            None, {keyword}
        )
        return await self.send_embed_msg(
            ctx,
            title="Allowlist Modified",
            description="Added `{whitelisted}` to the allowlist.".format(
                whitelisted=keyword
            ),
        )

    @command_audioset_global_whitelist.command(name="list", aliases=["show"])
    @commands.bot_has_permissions(add_reactions=True)
    async def command_audioset_global_whitelist_list(
        self, ctx: commands.Context
    ):
        """List all keywords added to the allowlist."""
        whitelist = (
            await self.config_cache.blacklist_whitelist.get_context_whitelist(
                None
            )
        )

        if not whitelist:
            return await self.send_embed_msg(
                ctx, title="Nothing in the allowlist."
            )
        whitelist = sorted(whitelist)
        text = ""
        total = len(whitelist)
        pages = []
        for i, entry in enumerate(whitelist, 1):
            text += f"{i}. [{entry}]"
            if i != total:
                text += "\n"
                if i % 10 == 0:
                    pages.append(box(text, lang="ini"))
                    text = ""
            else:
                pages.append(box(text, lang="ini"))
        embed_colour = await ctx.embed_colour()
        pages = [
            discord.Embed(
                title="Global Allowlist", description=page, colour=embed_colour
            )
            for page in pages
        ]

        await menu(ctx, pages, DEFAULT_CONTROLS)

    @command_audioset_global_whitelist.command(name="clear", aliases=["reset"])
    async def command_audioset_global_whitelist_clear(
        self, ctx: commands.Context
    ):
        """Clear all keywords from the allowlist."""
        whitelist = await self.config_cache.blacklist_whitelist.get_whitelist(
            None
        )
        if not whitelist:
            return await self.send_embed_msg(
                ctx, title="Nothing in the allowlist."
            )
        await self.config_cache.blacklist_whitelist.clear_whitelist()
        return await self.send_embed_msg(
            ctx,
            title="Allowlist Modified",
            description="All entries have been removed from the allowlist.",
        )

    @command_audioset_global_whitelist.command(
        name="delete", aliases=["del", "remove"]
    )
    async def command_audioset_global_whitelist_delete(
        self, ctx: commands.Context, *, keyword: str
    ):
        """Removes a keyword from the allowlist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.remove_from_whitelist(
            None, {keyword}
        )
        return await self.send_embed_msg(
            ctx,
            title="Allowlist Modified",
            description="Removed `{whitelisted}` from the allowlist.".format(
                whitelisted=keyword
            ),
        )

    @command_audioset_global.group(
        name="denylist", aliases=["blacklist", "disallowlist", "blocklist"]
    )
    async def command_audioset_global_blacklist(self, ctx: commands.Context):
        """Manages the global keyword denylist."""

    @command_audioset_global_blacklist.command(name="add")
    async def command_audioset_global_blacklist_add(
        self, ctx: commands.Context, *, keyword: str
    ):
        """Adds a keyword to the denylist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.add_to_blacklist(
            None, {keyword}
        )
        return await self.send_embed_msg(
            ctx,
            title="Denylist Modified",
            description="Added `{blacklisted}` to the denylist.".format(
                blacklisted=keyword
            ),
        )

    @command_audioset_global_blacklist.command(name="list", aliases=["show"])
    @commands.bot_has_permissions(add_reactions=True)
    async def command_audioset_global_blacklist_list(
        self, ctx: commands.Context
    ):
        """List all keywords added to the denylist."""
        blacklist = (
            await self.config_cache.blacklist_whitelist.get_context_blacklist(
                None
            )
        )
        if not blacklist:
            return await self.send_embed_msg(
                ctx, title="Nothing in the denylist."
            )
        blacklist = sorted(blacklist)
        text = ""
        total = len(blacklist)
        pages = []
        for i, entry in enumerate(blacklist, 1):
            text += f"{i}. [{entry}]"
            if i != total:
                text += "\n"
                if i % 10 == 0:
                    pages.append(box(text, lang="ini"))
                    text = ""
            else:
                pages.append(box(text, lang="ini"))
        embed_colour = await ctx.embed_colour()
        pages = [
            discord.Embed(
                title="Global Denylist", description=page, colour=embed_colour
            )
            for page in pages
        ]

        await menu(ctx, pages, DEFAULT_CONTROLS)

    @command_audioset_global_blacklist.command(name="clear", aliases=["reset"])
    async def command_audioset_global_blacklist_clear(
        self, ctx: commands.Context
    ):
        """Clear all keywords added to the denylist."""
        blacklist = await self.config_cache.blacklist_whitelist.get_blacklist(
            None
        )
        if not blacklist:
            return await self.send_embed_msg(
                ctx, title="Nothing in the denylist."
            )
        await self.config_cache.blacklist_whitelist.clear_blacklist(None)
        return await self.send_embed_msg(
            ctx,
            title="Denylist Modified",
            description="All entries have been removed from the denylist.",
        )

    @command_audioset_global_blacklist.command(
        name="delete", aliases=["del", "remove"]
    )
    async def command_audioset_global_blacklist_delete(
        self, ctx: commands.Context, *, keyword: str
    ):
        """Removes a keyword from the denylist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.remove_from_blacklist(
            None, {keyword}
        )
        return await self.send_embed_msg(
            ctx,
            title="Denylist Modified",
            description="Removed `{blacklisted}` from the denylist.".format(
                blacklisted=keyword
            ),
        )

    @command_audioset_global.command(name="restrict")
    async def command_audioset_global_restrict(self, ctx: commands.Context):
        """Toggle the domain restriction on Audio.

        When toggled off, users will be able to play songs from non-commercial websites and links.
        When toggled on, users are restricted to YouTube, SoundCloud, Vimeo, Twitch, and Bandcamp links.
        """
        restrict = await self.config_cache.url_restrict.get_global()
        await self.config_cache.url_restrict.set_global(not restrict)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Commercial links only globally: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE if not restrict else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="status")
    async def command_audioset_global_status(self, ctx: commands.Context):
        """Enable/disable tracks' titles as status."""
        status = await self.config_cache.status.get_global()
        await self.config_cache.status.set_global(not status)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Song titles as status: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE if not status else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="cache")
    async def command_audioset_global_cache(
        self, ctx: commands.Context, *, level: int = None
    ):
        """Sets the caching level.

        Level can be one of the following:

        0: Disables all caching
        1: Enables Spotify Cache
        2: Enables YouTube Cache
        3: Enables Lavalink Cache
        5: Enables all Caches

        If you wish to disable a specific cache use a negative number.
        """
        current_level = await self.config_cache.local_cache_level.get_global()
        spotify_cache = CacheLevel.set_spotify()
        youtube_cache = CacheLevel.set_youtube()
        lavalink_cache = CacheLevel.set_lavalink()
        has_spotify_cache = current_level.is_superset(spotify_cache)
        has_youtube_cache = current_level.is_superset(youtube_cache)
        has_lavalink_cache = current_level.is_superset(lavalink_cache)

        if level is None:
            msg = (
                "Max age:          [{max_age}]\n"
                + "Spotify cache:    [{spotify_status}]\n"
                + "Youtube cache:    [{youtube_status}]\n"
                + "Lavalink cache:   [{lavalink_status}]\n"
            ).format(
                max_age=str(
                    await self.config_cache.local_cache_age.get_global()
                )
                + " "
                + "days",
                spotify_status=ENABLED_TITLE
                if has_spotify_cache
                else DISABLED_TITLE,
                youtube_status=ENABLED_TITLE
                if has_youtube_cache
                else DISABLED_TITLE,
                lavalink_status=ENABLED_TITLE
                if has_lavalink_cache
                else DISABLED_TITLE,
            )
            await self.send_embed_msg(
                ctx,
                title="Cache Settings",
                description=box(msg, lang="ini"),
                no_embed=True,
            )
            return await ctx.send_help()
        if level not in [5, 3, 2, 1, 0, -1, -2, -3]:
            return await ctx.send_help()

        removing = level < 0

        if level == 5:
            newcache = CacheLevel.all()
        elif level == 0:
            newcache = CacheLevel.none()
        elif level in [-3, 3]:
            if removing:
                newcache = current_level - lavalink_cache
            else:
                newcache = current_level + lavalink_cache
        elif level in [-2, 2]:
            if removing:
                newcache = current_level - youtube_cache
            else:
                newcache = current_level + youtube_cache
        elif level in [-1, 1]:
            if removing:
                newcache = current_level - spotify_cache
            else:
                newcache = current_level + spotify_cache
        else:
            return await ctx.send_help()

        has_spotify_cache = newcache.is_superset(spotify_cache)
        has_youtube_cache = newcache.is_superset(youtube_cache)
        has_lavalink_cache = newcache.is_superset(lavalink_cache)
        msg = (
            "Max age:          [{max_age}]\n"
            + "Spotify cache:    [{spotify_status}]\n"
            + "Youtube cache:    [{youtube_status}]\n"
            + "Lavalink cache:   [{lavalink_status}]\n"
        ).format(
            max_age=str(await self.config_cache.local_cache_age.get_global())
            + " "
            + "days",
            spotify_status=ENABLED_TITLE
            if has_spotify_cache
            else DISABLED_TITLE,
            youtube_status=ENABLED_TITLE
            if has_youtube_cache
            else DISABLED_TITLE,
            lavalink_status=ENABLED_TITLE
            if has_lavalink_cache
            else DISABLED_TITLE,
        )

        await self.send_embed_msg(
            ctx,
            title="Cache Settings",
            description=box(msg, lang="ini"),
            no_embed=True,
        )
        await self.config_cache.local_cache_level.set_global(newcache.value)

    @command_audioset_global.command(name="cacheage")
    async def command_audioset_cacheage(self, ctx: commands.Context, age: int):
        """Sets the cache max age.

        This commands allows you to set the max number of days before an entry in the cache becomes
        invalid.
        """
        msg = ""
        if age < 7:
            msg = (
                "Cache age cannot be less than 7 days. If you wish to disable it run "
                "{prefix}audioset cache.\n"
            ).format(prefix=ctx.prefix)
            age = 7
        msg += "I've set the cache age to {age} days".format(age=age)
        await self.config_cache.local_cache_age.set_global(age)
        await self.send_embed_msg(
            ctx, title="Setting Changed", description=msg
        )

    @command_audioset_global.group(name="globalapi")
    async def command_audioset_global_globalapi(self, ctx: commands.Context):
        """Change globalapi settings."""

    @command_audioset_global_globalapi.command(name="toggle")
    async def command_audioset_global_globalapi_toggle(
        self, ctx: commands.Context
    ):
        """Toggle the server settings.

        Default is ON
        """
        state = await self.config_cache.global_api.get_context_value(ctx.guild)
        await self.config_cache.global_api.set_global(not state)
        if (
            not state
        ):  # Ensure a call is made if the API is enabled to update user perms
            self.global_api_user = (
                await self.api_interface.global_cache_api.get_perms()
            )

        msg = "Global DB is {status}".format(
            status=ENABLED if not state else DISABLED
        )
        await self.send_embed_msg(
            ctx, title="Setting Changed", description=msg
        )

    @command_audioset_global_globalapi.command(name="timeout")
    async def command_audioset_global_globalapi_timeout(
        self, ctx: commands.Context, timeout: Union[float, int]
    ):
        """Set GET request timeout.

        Example: 0.1 = 100ms 1 = 1 second
        """

        await self.config_cache.global_api_timeout.set_global(timeout)
        await ctx.send(
            "Request timeout set to {time} second(s)".format(time=timeout)
        )

    @command_audioset_global.command(name="historicalqueue")
    async def command_audioset_global_historical_queue(
        self, ctx: commands.Context
    ):
        """Toggle global daily queues.

        Global daily queues creates a playlist for all tracks played today across all servers.
        """
        daily_playlists = (
            await self.config_cache.daily_global_playlist.get_global()
        )
        await self.config_cache.daily_global_playlist.set_global(
            not daily_playlists
        )
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Global historical queues: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not daily_playlists
                else DISABLED_TITLE
            ),
        )

    @command_audioset_global.command(name="info", aliases=["settings"])
    async def command_audioset_global_info(self, ctx: commands.Context):
        """Display global settings."""
        current_level = await self.config_cache.local_cache_level.get_global()
        spotify_cache = CacheLevel.set_spotify()
        youtube_cache = CacheLevel.set_youtube()
        lavalink_cache = CacheLevel.set_lavalink()
        has_spotify_cache = current_level.is_superset(spotify_cache)
        has_youtube_cache = current_level.is_superset(youtube_cache)
        has_lavalink_cache = current_level.is_superset(lavalink_cache)
        global_api_enabled = await self.config_cache.global_api.get_global()
        global_api_get_timeout = (
            await self.config_cache.global_api_timeout.get_global()
        )
        empty_dc_enabled = await self.config_cache.empty_dc.get_global()
        empty_dc_timer = await self.config_cache.empty_dc_timer.get_global()
        empty_pause_enabled = await self.config_cache.empty_pause.get_global()
        empty_pause_timer = (
            await self.config_cache.empty_pause_timer.get_global()
        )
        jukebox = await self.config_cache.jukebox.get_global()
        jukebox_price = await self.config_cache.jukebox_price.get_global()
        disconnect = await self.config_cache.disconnect.get_global()
        maxlength = await self.config_cache.max_track_length.get_global()
        song_status = await self.config_cache.status.get_global()
        persist_queue = await self.config_cache.persistent_queue.get_global()
        auto_deafen = await self.config_cache.auto_deafen.get_global()
        lyrics = await self.config_cache.prefer_lyrics.get_global()
        restrict = await self.config_cache.url_restrict.get_global()
        volume = await self.config_cache.volume.get_global()
        thumbnail = await self.config_cache.thumbnail.get_global()
        max_queue = await self.config_cache.max_queue_size.get_global()
        country_code = await self.config_cache.country_code.get_global()
        historical_playlist = (
            await self.config_cache.daily_global_playlist.get_global()
        )
        auto_lyrics = await self.config_cache.auto_lyrics.get_global()
        disabled = DISABLED_TITLE
        enabled = ENABLED_TITLE

        msg = "----" + "Global Settings" + "----        \n"

        msg += (
            "Songs as status:              [{status}]\n"
            "Historical playlist:          [{historical_playlist}]\n"
            "Default persist queue:        [{persist_queue}]\n"
            "Default Spotify search:       [{countrycode}]\n"
        ).format(
            status=enabled if song_status else disabled,
            countrycode=country_code,
            historical_playlist=enabled if historical_playlist else disabled,
            persist_queue=enabled if persist_queue else disabled,
        )

        over_notify = await self.config_cache.notify.get_global()
        over_daily_playlist = (
            await self.config_cache.daily_playlist.get_global()
        )
        msg += (
            "\n---"
            + "Global Rules"
            + "---        \n"
            + (
                "Allow notify messages:        [{notify}]\n"
                "Allow daily playlist:         [{daily_playlist}]\n"
                "Allow Auto-Lyrics:            [{auto_lyrics}]\n"
                "Enforced auto-disconnect:     [{dc}]\n"
                "Enforced empty dc:            [{empty_dc_enabled}]\n"
                "Empty dc timer:               [{dc_num_seconds}]\n"
                "Enforced empty pause:         [{empty_pause_enabled}]\n"
                "Empty pause timer:            [{pause_num_seconds}]\n"
                "Enforced jukebox:             [{jukebox}]\n"
                "Command price:                [{jukebox_price}]\n"
                "Enforced max queue length:    [{max_queue}]\n"
                "Enforced max track length:    [{tracklength}]\n"
                "Enforced auto-deafen:         [{auto_deafen}]\n"
                "Enforced thumbnails:          [{thumbnail}]\n"
                "Enforced maximum volume:      [{volume}%]\n"
                "Enforced URL restrict:        [{restrict}]\n"
                "Enforced prefer lyrics:       [{lyrics}]\n"
            )
        ).format(
            notify=over_notify,
            daily_playlist=over_daily_playlist,
            dc=enabled if disconnect else disabled,
            dc_num_seconds=self.get_time_string(empty_dc_timer),
            empty_pause_enabled=enabled if empty_pause_enabled else disabled,
            empty_dc_enabled=enabled if empty_dc_enabled else disabled,
            pause_num_seconds=self.get_time_string(empty_pause_timer),
            jukebox=enabled if jukebox else disabled,
            jukebox_price=humanize_number(jukebox_price),
            tracklength=self.get_time_string(maxlength),
            volume=volume,
            restrict=enabled if restrict else disabled,
            auto_deafen=enabled if auto_deafen else disabled,
            thumbnail=enabled if thumbnail else disabled,
            max_queue=humanize_number(max_queue),
            lyrics=enabled if lyrics else disabled,
            auto_lyrics=enabled if auto_lyrics else disabled,
        )

        msg += (
            "\n---"
            + "Cache Settings"
            + "---        \n"
            + "Max age:                [{max_age}]\n"
            + "Local Spotify cache:    [{spotify_status}]\n"
            + "Local Youtube cache:    [{youtube_status}]\n"
            + "Local Lavalink cache:   [{lavalink_status}]\n"
            + "Global cache status:    [{global_cache}]\n"
            + "Global timeout:         [{num_seconds}]\n"
        ).format(
            max_age=str(await self.config_cache.local_cache_age.get_global())
            + " "
            + "days",
            spotify_status=ENABLED_TITLE
            if has_spotify_cache
            else DISABLED_TITLE,
            youtube_status=ENABLED_TITLE
            if has_youtube_cache
            else DISABLED_TITLE,
            lavalink_status=ENABLED_TITLE
            if has_lavalink_cache
            else DISABLED_TITLE,
            global_cache=ENABLED_TITLE
            if global_api_enabled
            else DISABLED_TITLE,
            num_seconds=self.get_time_string(global_api_get_timeout),
        )

        await self.send_embed_msg(
            ctx, description=box(msg, lang="ini"), no_embed=True
        )

    # --------------------------- CHANNEL COMMANDS ----------------------------

    @command_audioset.group(name="channel")
    @commands.guild_only()
    async def command_audioset_channel(self, ctx: commands.Context):
        """Channel configuration options."""

    @command_audioset_channel.command(name="volume")
    async def command_audioset_channel_volume(
        self, ctx: commands.Context, channel: discord.VoiceChannel, volume: int
    ):
        """Set the maximum allowed volume to be set on the specified channel."""
        dj_enabled = await self.config_cache.dj_status.get_context_value(
            ctx.guild
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (
            dj_enabled
            and not can_skip
            and not await self._has_dj_role(ctx, ctx.author)
        ):
            return await self.send_embed_msg(
                ctx,
                title="Unable To Change Volume",
                description="You need the DJ role to change the volume.",
            )
        (
            global_value,
            guild_value,
            __,
        ) = await self.config_cache.volume.get_context_max(ctx.guild)
        max_value = min(global_value, guild_value)
        if not 10 < volume <= max_value:
            await self.send_embed_msg(
                ctx,
                title="Invalid Setting",
                description="Maximum allowed volume has to be between 10% and {cap}%.".format(
                    cap=max_value
                ),
            )
            return
        await self.config_cache.volume.set_channel(channel, volume)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Maximum allowed volume set to: {volume}%.".format(
                volume=volume
            ),
        )

    @command_audioset_channel.command(
        name="info", aliases=["settings", "config"]
    )
    async def command_audioset_channel_settings(
        self, ctx: commands.Context, channel: discord.VoiceChannel
    ):
        """Show the settings for the specified channel."""

        volume = await self.config_cache.volume.get_channel(channel)
        msg = (
            "----"
            + "Channel Settings"
            + "----        \nVolume:   [{vol}%]\n".format(
                vol=volume,
            )
        )
        await self.send_embed_msg(
            ctx, description=box(msg, lang="ini"), no_embed=True
        )

    # --------------------------- SERVER COMMANDS ----------------------------

    @command_audioset.group(name="server", aliases=["guild"])
    @commands.guild_only()
    async def command_audioset_guild(self, ctx: commands.Context):
        """Server configuration options."""

    @command_audioset_guild.group(name="allowlist", aliases=["whitelist"])
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_whitelist(self, ctx: commands.Context):
        """Manages the keyword allowlist."""

    @command_audioset_guild_whitelist.command(name="add")
    async def command_audioset_guild_whitelist_add(
        self, ctx: commands.Context, *, keyword: str
    ):
        """Adds a keyword to the allowlist.

        If anything is added to allowlist, it will reject everything else.
        """
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.add_to_whitelist(
            ctx.guild, {keyword}
        )
        return await self.send_embed_msg(
            ctx,
            title="Allowlist Modified",
            description="Added `{whitelisted}` to the allowlist.".format(
                whitelisted=keyword
            ),
        )

    @command_audioset_guild_whitelist.command(name="list", aliases=["show"])
    @commands.bot_has_permissions(add_reactions=True)
    async def command_audioset_guild_whitelist_list(
        self, ctx: commands.Context
    ):
        """List all keywords added to the allowlist."""
        whitelist = (
            await self.config_cache.blacklist_whitelist.get_context_whitelist(
                ctx.guild, printable=True
            )
        )
        if not whitelist:
            return await self.send_embed_msg(
                ctx, title="Nothing in the allowlist."
            )
        whitelist = sorted(whitelist)
        text = ""
        total = len(whitelist)
        pages = []
        for i, entry in enumerate(whitelist, 1):
            text += f"{i}. [{entry}]"
            if i != total:
                text += "\n"
                if i % 10 == 0:
                    pages.append(box(text, lang="ini"))
                    text = ""
            else:
                pages.append(box(text, lang="ini"))
        embed_colour = await ctx.embed_colour()
        pages = [
            discord.Embed(
                title="Allowlist", description=page, colour=embed_colour
            )
            for page in pages
        ]

        await menu(ctx, pages, DEFAULT_CONTROLS)

    @command_audioset_guild_whitelist.command(name="clear", aliases=["reset"])
    async def command_audioset_guild_whitelist_clear(
        self, ctx: commands.Context
    ):
        """Clear all keywords from the allowlist."""
        whitelist = await self.config_cache.blacklist_whitelist.get_whitelist(
            ctx.guild
        )
        if not whitelist:
            return await self.send_embed_msg(
                ctx, title="Nothing in the allowlist."
            )
        await self.config_cache.blacklist_whitelist.clear_whitelist(ctx.guild)
        return await self.send_embed_msg(
            ctx,
            title="Allowlist Modified",
            description="All entries have been removed from the allowlist.",
        )

    @command_audioset_guild_whitelist.command(
        name="delete", aliases=["del", "remove"]
    )
    async def command_audioset_guild_whitelist_delete(
        self, ctx: commands.Context, *, keyword: str
    ):
        """Removes a keyword from the allowlist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.remove_from_whitelist(
            ctx.guild, {keyword}
        )
        return await self.send_embed_msg(
            ctx,
            title="Allowlist Modified",
            description="Removed `{whitelisted}` from the allowlist.".format(
                whitelisted=keyword
            ),
        )

    @command_audioset_guild.group(
        name="denylist", aliases=["blacklist", "disallowlist", "blocklist"]
    )
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_blacklist(self, ctx: commands.Context):
        """Manages the keyword denylist."""

    @command_audioset_guild_blacklist.command(name="add")
    async def command_audioset_guild_blacklist_add(
        self, ctx: commands.Context, *, keyword: str
    ):
        """Adds a keyword to the denylist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.add_to_blacklist(
            ctx.guild, {keyword}
        )
        return await self.send_embed_msg(
            ctx,
            title="Denylist Modified",
            description="Added `{blacklisted}` to the denylist.".format(
                blacklisted=keyword
            ),
        )

    @command_audioset_guild_blacklist.command(name="list", aliases=["show"])
    @commands.bot_has_permissions(add_reactions=True)
    async def command_audioset_guild_blacklist_list(
        self, ctx: commands.Context
    ):
        """List all keywords added to the denylist."""
        blacklist = (
            await self.config_cache.blacklist_whitelist.get_context_blacklist(
                ctx.guild, printable=True
            )
        )
        if not blacklist:
            return await self.send_embed_msg(
                ctx, title="Nothing in the denylist."
            )
        blacklist = sorted(blacklist)
        text = ""
        total = len(blacklist)
        pages = []
        for i, entry in enumerate(blacklist, 1):
            text += f"{i}. [{entry}]"
            if i != total:
                text += "\n"
                if i % 10 == 0:
                    pages.append(box(text, lang="ini"))
                    text = ""
            else:
                pages.append(box(text, lang="ini"))
        embed_colour = await ctx.embed_colour()
        pages = [
            discord.Embed(
                title="Denylist", description=page, colour=embed_colour
            )
            for page in pages
        ]

        await menu(ctx, pages, DEFAULT_CONTROLS)

    @command_audioset_guild_blacklist.command(name="clear", aliases=["reset"])
    async def command_audioset_guild_blacklist_clear(
        self, ctx: commands.Context
    ):
        """Clear all keywords added to the denylist."""
        await self.config_cache.blacklist_whitelist.clear_blacklist(ctx.guild)
        return await self.send_embed_msg(
            ctx,
            title="Denylist Modified",
            description="All entries have been removed from the denylist.",
        )

    @command_audioset_guild_blacklist.command(
        name="delete", aliases=["del", "remove"]
    )
    async def command_audioset_guild_blacklist_delete(
        self, ctx: commands.Context, *, keyword: str
    ):
        """Removes a keyword from the denylist."""
        keyword = keyword.lower().strip()
        if not keyword:
            return await ctx.send_help()
        await self.config_cache.blacklist_whitelist.remove_from_blacklist(
            ctx.guild, {keyword}
        )
        return await self.send_embed_msg(
            ctx,
            title="Denylist Modified",
            description="Removed `{blacklisted}` from the denylist.".format(
                blacklisted=keyword
            ),
        )

    @command_audioset_guild.command(name="volume")
    async def command_audioset_guild_volume(
        self, ctx: commands.Context, volume: int
    ):
        """Set the maximum allowed volume to be set."""
        dj_enabled = await self.config_cache.dj_status.get_context_value(
            ctx.guild
        )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (
            dj_enabled
            and not can_skip
            and not await self._has_dj_role(ctx, ctx.author)
        ):
            return await self.send_embed_msg(
                ctx,
                title="Unable To Change Volume",
                description="You need the DJ role to change the volume.",
            )

        global_value, __, __ = await self.config_cache.volume.get_context_max(
            ctx.guild
        )
        if not 10 < volume <= global_value:
            await self.send_embed_msg(
                ctx,
                title="Invalid Setting",
                description="Maximum allowed volume has to be between 10% and {cap}%.".format(
                    cap=global_value
                ),
            )
            return
        await self.config_cache.volume.set_guild(ctx.guild, volume)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Maximum allowed volume set to: {volume}%.".format(
                volume=volume
            ),
        )

    @command_audioset_guild.command(name="maxqueue")
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_maxqueue(
        self, ctx: commands.Context, size: int
    ):
        """Set the maximum size a queue is allowed to be.

        Set to -1 to use the maximum value allowed by the bot.
        """
        global_value = await self.config_cache.max_queue_size.get_global()

        if not 10 < size < global_value:
            return await self.send_embed_msg(
                ctx,
                title="Invalid Queue Size",
                description="Queue size must bet between 10 and {cap}.".format(
                    cap=humanize_number(global_value)
                ),
            )
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Maximum queue size allowed is now {size}.".format(
                size=humanize_number(size)
            ),
        )
        if size < 0:
            size = None
        await self.config_cache.max_queue_size.set_guild(ctx.guild, size)

    @command_audioset_guild.command(name="dailyqueue")
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_daily_queue(self, ctx: commands.Context):
        """Toggle daily queues.

        Daily queues creates a playlist for all tracks played today.
        """

        if await self.config_cache.daily_playlist.get_global() is False:
            await self.config_cache.daily_playlist.set_guild(ctx.guild, False)
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description=(
                    "Daily queues: {true_or_false}, "
                    "\n\n**Reason**: The bot owner has disabled this feature."
                ).format(true_or_false=DISABLED_TITLE),
            )

        daily_playlists = await self.config_cache.daily_playlist.get_guild(
            ctx.guild
        )
        await self.config_cache.daily_playlist.set_guild(
            ctx.guild, not daily_playlists
        )
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Daily queues: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not daily_playlists
                else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(name="disconnect", aliases=["dc"])
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_dc(self, ctx: commands.Context):
        """Toggle the bot auto-disconnecting when done playing.

        This setting takes precedence over `[p]audioset server emptydisconnect`.
        """

        if await self.config_cache.disconnect.get_global() is True:
            await self.config_cache.disconnect.set_guild(ctx.guild, True)
            await self.config_cache.autoplay.set_guild(ctx.guild, False)
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description=(
                    "Auto-disconnection at queue end: {true_or_false}\n"
                    "Auto-play has been disabled."
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(true_or_false=ENABLED_TITLE),
            )

        disconnect = await self.config_cache.disconnect.get_guild(ctx.guild)
        autoplay = await self.config_cache.autoplay.get_guild(ctx.guild)
        msg = ""
        msg += "Auto-disconnection at queue end: {true_or_false}.".format(
            true_or_false=ENABLED_TITLE if not disconnect else DISABLED_TITLE
        )
        if disconnect is not True and autoplay is True:
            msg += "\nAuto-play has been disabled."
            await self.config_cache.autoplay.set_guild(ctx.guild, False)

        await self.config_cache.disconnect.set_guild(ctx.guild, not disconnect)

        await self.send_embed_msg(
            ctx, title="Setting Changed", description=msg
        )

    @command_audioset_guild.command(name="dj")
    @commands.admin_or_permissions(manage_roles=True)
    async def command_audioset_guild_dj(self, ctx: commands.Context):
        """Toggle DJ mode.

        DJ mode allows users with the DJ role to use audio commands.
        """
        dj_role = await self.config_cache.dj_roles.get_guild(ctx.guild)
        if not dj_role:
            await self.send_embed_msg(
                ctx,
                title="Missing DJ Role",
                description=(
                    "Please set a role to use with DJ mode. Enter the role name or ID now."
                ),
            )

            try:
                pred = MessagePredicate.valid_role(ctx)
                await self.bot.wait_for("message", timeout=15.0, check=pred)
                await ctx.invoke(
                    self.command_audioset_guild_role_create,
                    role_name=pred.result,
                )
            except asyncio.TimeoutError:
                return await self.send_embed_msg(
                    ctx, title="Response timed out, try again later."
                )
        dj_enabled = await self.config_cache.dj_status.get_guild(ctx.guild)
        await self.config_cache.dj_status.set_guild(ctx.guild, not dj_enabled)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="DJ role: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not dj_enabled
                else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(
        name="emptydisconnect", aliases=["emptydc"]
    )
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_emptydisconnect(
        self, ctx: commands.Context, seconds: int
    ):
        """Auto-disconnect from channel when bot is alone in it for x seconds, 0 to disable.

        `[p]audioset server dc` takes precedence over this setting.
        """

        if await self.config_cache.empty_dc.get_global() is True:
            await self.config_cache.empty_dc.set_guild(ctx.guild, True)
            seconds = await self.config_cache.empty_dc_timer.get_global()
            await self.config_cache.empty_dc_timer.set_guild(
                ctx.guild, seconds
            )
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description=(
                    "Empty disconnect: {true_or_false}\n"
                    "Empty disconnect timer set to: {time_to_auto_dc}\n"
                    "Auto-play has been disabled."
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(
                    true_or_false=ENABLED_TITLE,
                    time_to_auto_dc=self.get_time_string(seconds),
                ),
            )

        if seconds < 0:
            return await self.send_embed_msg(
                ctx,
                title="Invalid Time",
                description="Seconds can't be less than zero.",
            )
        if 10 > seconds > 0:
            seconds = 10
        if seconds == 0:
            enabled = False
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Empty disconnect disabled.",
            )
        else:
            enabled = True
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Empty disconnect timer set to {num_seconds}.".format(
                    num_seconds=self.get_time_string(seconds)
                ),
            )
        await self.config_cache.empty_dc_timer.set_guild(ctx.guild, seconds)
        await self.config_cache.empty_dc.set_guild(ctx.guild, enabled)

    @command_audioset_guild.command(name="emptypause")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_emptypause(
        self, ctx: commands.Context, seconds: int
    ):
        """Auto-pause after x seconds when room is empty, 0 to disable."""
        if await self.config_cache.empty_pause.get_global() is True:
            await self.config_cache.empty_pause.set_guild(ctx.guild, True)
            seconds = await self.config_cache.empty_pause_timer.get_global()
            await self.config_cache.empty_pause_timer.set_guild(
                ctx.guild, seconds
            )
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description=(
                    "Empty pause: {true_or_false}\n"
                    "Empty pause timer set to: {time_to_auto_dc}\n"
                    "Auto-play has been disabled."
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(
                    true_or_false=ENABLED_TITLE,
                    time_to_auto_dc=self.get_time_string(seconds),
                ),
            )

        if seconds < 0:
            return await self.send_embed_msg(
                ctx,
                title="Invalid Time",
                description="Seconds can't be less than zero.",
            )
        if 10 > seconds > 0:
            seconds = 10
        if seconds == 0:
            enabled = False
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Empty pause disabled.",
            )
        else:
            enabled = True
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Empty pause timer set to {num_seconds}.".format(
                    num_seconds=self.get_time_string(seconds)
                ),
            )
        await self.config_cache.empty_pause_timer.set_guild(ctx.guild, seconds)
        await self.config_cache.empty_pause.set_guild(ctx.guild, enabled)

    @command_audioset_guild.command(name="lyrics")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_lyrics(self, ctx: commands.Context):
        """Prioritise tracks with lyrics."""

        if await self.config_cache.prefer_lyrics.get_global() is True:
            await self.config_cache.prefer_lyrics.set_guild(ctx.guild, True)
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description=(
                    "Prefer tracks with lyrics: {true_or_false}."
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(true_or_false=ENABLED_TITLE),
            )

        prefer_lyrics = await self.config_cache.prefer_lyrics.get_guild(
            ctx.guild
        )
        await self.config_cache.prefer_lyrics.set_guild(
            ctx.guild, not prefer_lyrics
        )
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Prefer tracks with lyrics: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not prefer_lyrics
                else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(name="jukebox")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_jukebox(
        self, ctx: commands.Context, price: int
    ):
        """Set a price for queueing tracks for non-mods, 0 to disable."""
        if (
            await self.config_cache.jukebox.get_global() is True
            and await bank.is_global()
        ):
            await self.config_cache.jukebox.set_guild(ctx.guild, True)
            jukebox_price = await self.config_cache.jukebox_price.get_global()
            await self.config_cache.jukebox_price.set_guild(
                ctx.guild, jukebox_price
            )
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description=(
                    "Jukebox Mode: {true_or_false}\n"
                    "Price per command: {cost} {currency}\n"
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(
                    true_or_false=ENABLED_TITLE,
                    cost=humanize_number(jukebox_price),
                    currency=await bank.get_currency_name(ctx.guild),
                ),
            )
        if price < 0:
            return await self.send_embed_msg(
                ctx,
                title="Invalid Price",
                description="Price can't be less than zero.",
            )
        elif price > 2 ** 63 - 1:
            return await self.send_embed_msg(
                ctx,
                title="Invalid Price",
                description="Price can't be greater or equal to than 2^63.",
            )
        elif price == 0:
            jukebox = False
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Jukebox mode disabled.",
            )
        else:
            jukebox = True
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Jukebox mode enabled, command price set to {price} {currency}."
                ).format(
                    price=humanize_number(price),
                    currency=await bank.get_currency_name(ctx.guild),
                ),
            )

        await self.config_cache.jukebox_price.set_guild(ctx.guild, price)
        await self.config_cache.jukebox.set_guild(ctx.guild, jukebox)

    @command_audioset_guild.group(name="djrole", aliases=["role"])
    @commands.admin_or_permissions(manage_roles=True)
    async def command_audioset_guild_role(self, ctx: commands.Context):
        """Add/Remove/Show DJ Role and members."""

    @command_audioset_guild_role.command(name="create", aliases=["add"])
    async def command_audioset_guild_role_create(
        self, ctx: commands.Context, *, role_name: discord.Role
    ):
        """Add a role from DJ mode allowlist.

        See roles with `[p]audioset server role list`
        Remove roles with `[p]audioset server role remove`
        See DJs with `[p]audioset server role members`
        """
        await self.config_cache.dj_roles.add_guild(ctx.guild, {role_name})
        await self.send_embed_msg(
            ctx,
            title="Settings Changed",
            description="Role added to DJ list: {role.name}.".format(
                role=role_name
            ),
        )

    @command_audioset_guild_role.command(
        name="delete", aliases=["remove", "del"]
    )
    async def command_audioset_guild_role_delete(
        self, ctx: commands.Context, *, role_name: discord.Role
    ):
        """Remove a role from DJ mode allowlist.

        Add roles with `[p]audioset server role add`
        See roles with `[p]audioset server role list`
        See DJs with `[p]audioset server role members`
        """
        await self.config_cache.dj_roles.remove_guild(ctx.guild, {role_name})
        await self.send_embed_msg(
            ctx,
            title="Settings Changed",
            description="Role removed from DJ list: {role.name}.".format(
                role=role_name
            ),
        )

    @command_audioset_guild_role.command(name="list", aliases=["show"])
    async def command_audioset_guild_role_list(self, ctx: commands.Context):
        """Show all roles from DJ mode allowlist.

        Add roles with `[p]audioset server role add`
        Remove roles with `[p]audioset server role remove`
        See DJs with `[p]audioset server role members`
        """
        roles = await self.config_cache.dj_roles.get_context_value(ctx.guild)
        roles = sorted(roles, key=attrgetter("position"), reverse=True)
        rolestring = "\n".join(r.name for r in roles)
        pages = pagify(rolestring, page_length=500)
        await ctx.send_interactive(pages, timeout=30)

    @command_audioset_guild_role.command(name="members")
    async def command_audioset_guild_role_members(self, ctx: commands.Context):
        """Show all users with DJ permission.

        Add roles with `[p]audioset server role add`
        Remove roles with `[p]audioset serverrole remove`
        See roles with `[p]audioset server role list`
        """
        djs = await self.config_cache.dj_roles.get_allowed_members(ctx.guild)
        djs = sorted(
            djs,
            key=attrgetter("top_role.position", "display_name"),
            reverse=True,
        )
        memberstring = "\n".join(r.display_name for r in djs)
        pages = pagify(memberstring, page_length=500)
        await ctx.send_interactive(pages, timeout=30)

    @command_audioset_guild.command(name="maxlength")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_maxlength(
        self, ctx: commands.Context, seconds: Union[int, str]
    ):
        """Max length of a track to queue in seconds, 0 to disable.

        Accepts seconds or a value formatted like 00:00:00 (`hh:mm:ss`) or 00:00 (`mm:ss`). Invalid input will turn the max length setting off.
        """
        global_value = await self.config_cache.max_queue_size.get_global()
        if not isinstance(seconds, int):
            seconds = self.time_convert(seconds)
        if not 0 <= seconds <= global_value:
            return await self.send_embed_msg(
                ctx,
                title="Invalid length",
                description="Length can't be less than zero or greater than {cap}.".format(
                    cap=self.get_time_string(global_value)
                ),
            )
        if seconds == 0:
            if global_value != 0:
                await self.send_embed_msg(
                    ctx,
                    title="Setting Changed",
                    description="Track max length disabled.",
                )
            else:
                return await self.send_embed_msg(
                    ctx,
                    title="Setting Not Changed",
                    description=(
                        "Track max length cannot be disabled as it is restricted by the bot owner."
                    ),
                )
        else:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Track max length set to {seconds}.".format(
                    seconds=self.get_time_string(seconds)
                ),
            )
        await self.config_cache.max_track_length.set_guild(ctx.guild, seconds)

    @command_audioset_guild.command(name="notify")
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_notify(self, ctx: commands.Context):
        """Toggle track announcement and other bot messages."""
        if await self.config_cache.notify.get_global() is False:
            await self.config_cache.notify.set_guild(ctx.guild, False)
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description=(
                    "Notify mode: {true_or_false}, "
                    "\n\n**Reason**: The bot owner has disabled this feature."
                ).format(true_or_false=DISABLED_TITLE),
            )
        notify = await self.config_cache.notify.get_guild(ctx.guild)
        await self.config_cache.notify.set_guild(ctx.guild, not notify)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Notify mode: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE if not notify else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(name="autodeafen")
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_auto_deafen(self, ctx: commands.Context):
        """Toggle whether the bot will be auto deafened upon joining the voice channel."""
        if await self.config_cache.auto_deafen.get_global() is True:
            await self.config_cache.auto_deafen.set_guild(ctx.guild, True)
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description=(
                    "Auto-deafen: {true_or_false}."
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(true_or_false=ENABLED_TITLE),
            )
        auto_deafen = await self.config_cache.auto_deafen.get_guild(ctx.guild)
        await self.config_cache.auto_deafen.set_guild(
            ctx.guild, not auto_deafen
        )
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Auto-deafen: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not auto_deafen
                else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(name="restrict")
    @commands.admin_or_permissions(manage_guild=True)
    async def command_audioset_guild_restrict(self, ctx: commands.Context):
        """Toggle the domain restriction on Audio.

        When toggled off, users will be able to play songs from non-commercial websites and links.
        When toggled on, users are restricted to YouTube, SoundCloud, Twitch, and Bandcamp links.
        """
        if await self.config_cache.url_restrict.get_global() is True:
            await self.config_cache.url_restrict.set_guild(ctx.guild, True)
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description=(
                    "Commercial links only: {true_or_false}."
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(true_or_false=ENABLED_TITLE),
            )
        restrict = await self.config_cache.url_restrict.get_guild(ctx.guild)
        await self.config_cache.url_restrict.set_guild(ctx.guild, not restrict)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Commercial links only: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE if not restrict else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(name="thumbnail")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_thumbnail(self, ctx: commands.Context):
        """Toggle displaying a thumbnail on audio messages."""
        if await self.config_cache.thumbnail.get_global() is True:
            await self.config_cache.thumbnail.set_guild(ctx.guild, True)
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description=(
                    "Thumbnail display: {true_or_false}."
                    "\n\n**Reason**: The bot owner has enforced this feature."
                ).format(true_or_false=ENABLED_TITLE),
            )
        thumbnail = await self.config_cache.thumbnail.get_guild(ctx.guild)
        await self.config_cache.thumbnail.set_guild(ctx.guild, not thumbnail)
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Thumbnail display: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not thumbnail
                else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(name="vote")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_vote(
        self, ctx: commands.Context, percent: int
    ):
        """Percentage needed for non-mods to skip tracks, 0 to disable."""
        if percent < 0:
            return await self.send_embed_msg(
                ctx,
                title="Invalid percentage",
                description="Percentage can't be less than zero.",
            )
        elif percent > 100:
            percent = 100
        if percent == 0:
            enabled = False
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Voting disabled. All users can use queue management commands.",
            )
        else:
            enabled = True
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Vote percentage set to {percent}%.".format(
                    percent=percent
                ),
            )

        await self.config_cache.votes.set_guild(ctx.guild, enabled)
        await self.config_cache.votes_percentage.set_guild(ctx.guild, percent)

    @command_audioset_guild.command(name="countrycode")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_countrycode(
        self, ctx: commands.Context, country: str
    ):
        """Set the country code for Spotify searches."""
        if len(country) != 2:
            return await self.send_embed_msg(
                ctx,
                title="Invalid Country Code",
                description=(
                    "Please use an official [ISO 3166-1 alpha-2]"
                    "(https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code."
                ),
            )
        country = country.upper()
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Country Code set to {country}.".format(
                country=country
            ),
        )

        await self.config_cache.country_code.set_guild(ctx.guild, country)

    @command_audioset_guild.command(name="persistqueue")
    @commands.mod_or_permissions(administrator=True)
    async def command_audioset_guild_persist_queue(
        self, ctx: commands.Context
    ):
        """Toggle persistent queues.

        Persistent queues allows the current queue to be restored when the queue closes.
        """
        persist_cache = await self.config_cache.persistent_queue.get_guild(
            ctx.guild
        )
        await self.config_cache.persistent_queue.set_guild(
            ctx.guild, not persist_cache
        )
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Persisting queues: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not persist_cache
                else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.group(name="autoplay")
    @commands.mod_or_permissions(manage_guild=True)
    async def command_audioset_guild_autoplay(self, ctx: commands.Context):
        """Change auto-play setting."""

    @command_audioset_guild_autoplay.command(name="toggle")
    async def command_audioset_guild_autoplay_toggle(
        self, ctx: commands.Context
    ):
        """Toggle auto-play when there no songs in queue."""
        if await self.config_cache.disconnect.get_global() is True:
            await self.config_cache.disconnect.set_guild(ctx.guild, True)
            await self.config_cache.autoplay.set_guild(ctx.guild, False)
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description=(
                    "Auto-disconnection at queue end: {true_or_false}\n"
                    "Auto-play has been disabled."
                    "\n\n**Reason**: The bot owner has disabled this feature."
                ).format(true_or_false=ENABLED_TITLE),
            )

        autoplay = await self.config_cache.autoplay.get_guild(ctx.guild)
        repeat = await self.config_cache.repeat.get_guild(ctx.guild)
        disconnect = await self.config_cache.disconnect.get_guild(ctx.guild)
        msg = "Auto-play when queue ends: {true_or_false}.".format(
            true_or_false=ENABLED_TITLE if not autoplay else DISABLED_TITLE
        )
        await self.config_cache.autoplay.set_guild(ctx.guild, not autoplay)
        if autoplay is not True and repeat is True:
            msg += "\nRepeat has been disabled."
            await self.config_cache.repeat.set_guild(ctx.guild, False)
        if autoplay is not True and disconnect is True:
            msg += "\nAuto-disconnecting at queue end has been disabled."
            await self.config_cache.disconnect.set_guild(ctx.guild, False)

        await self.send_embed_msg(
            ctx, title="Setting Changed", description=msg
        )
        if self._player_check(ctx):
            await self.set_player_settings(ctx)

    @command_audioset_guild_autoplay.command(
        name="playlist", usage="<playlist_name_OR_id> [args]"
    )
    @commands.bot_has_permissions(add_reactions=True)
    async def command_audioset_guild_autoplay_playlist(
        self,
        ctx: commands.Context,
        playlist_matches: PlaylistConverter,
        *,
        scope_data: ScopeParser = None,
    ):
        """Set a playlist to auto-play songs from.

        **Usage**:
        ​ ​ ​ ​ `[p]audioset server autoplay playlist_name_OR_id [args]`

        **Args**:
        ​ ​ ​ ​ The following are all optional:
        ​ ​ ​ ​ ​ ​ ​ ​ --scope <scope>
        ​ ​ ​ ​ ​ ​ ​ ​ --author [user]
        ​ ​ ​ ​ ​ ​ ​ ​ --guild [guild] **Only the bot owner can use this**

        **Scope** is one of the following:
            ​Global
        ​ ​ ​ ​ Guild
        ​ ​ ​ ​ User

        **Author** can be one of the following:
        ​ ​ ​ ​ User ID
        ​ ​ ​ ​ User Mention
        ​ ​ ​ ​ User Name#123

        **Guild** can be one of the following:
        ​ ​ ​ ​ Guild ID
        ​ ​ ​ ​ Exact guild name

        Example use:
        ​ ​ ​ ​ `[p]audioset server autoplay MyGuildPlaylist`
        ​ ​ ​ ​ `[p]audioset server autoplay MyGlobalPlaylist --scope Global`
        ​ ​ ​ ​ `[p]audioset server autoplay PersonalPlaylist --scope User --author Draper`
        """
        if self.playlist_api is None:
            return await self.send_embed_msg(
                ctx,
                title="Playlists Are Not Available",
                description="The playlist section of Music is currently unavailable",
                footer=discord.Embed.Empty
                if not await self.bot.is_owner(ctx.author)
                else "Check your logs.",
            )
        if scope_data is None:
            scope_data = [None, ctx.author, ctx.guild, False]

        scope, author, guild, specified_user = scope_data
        try:
            playlist, playlist_arg, scope = await self.get_playlist_match(
                ctx, playlist_matches, scope, author, guild, specified_user
            )
        except TooManyMatches as e:
            return await self.send_embed_msg(ctx, title=str(e))
        if playlist is None:
            return await self.send_embed_msg(
                ctx,
                title="No Playlist Found",
                description="Could not match '{arg}' to a playlist".format(
                    arg=playlist_arg
                ),
            )
        try:
            tracks = playlist.tracks
            if not tracks:
                return await self.send_embed_msg(
                    ctx,
                    title="No Tracks Found",
                    description="Playlist {name} has no tracks.".format(
                        name=playlist.name
                    ),
                )
            playlist_data = dict(
                enabled=True, id=playlist.id, name=playlist.name, scope=scope
            )
            await self.config.guild(ctx.guild).autoplaylist.set(playlist_data)
        except RuntimeError:
            return await self.send_embed_msg(
                ctx,
                title="No Playlist Found",
                description="Playlist {id} does not exist in {scope} scope.".format(
                    id=playlist_arg, scope=self.humanize_scope(scope, the=True)
                ),
            )
        except MissingGuild:
            return await self.send_embed_msg(
                ctx,
                title="Missing Arguments",
                description="You need to specify the Guild ID for the guild to lookup.",
            )
        else:
            return await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Playlist {name} (`{id}`) [**{scope}**] will be used for autoplay."
                ).format(
                    name=playlist.name,
                    id=playlist.id,
                    scope=self.humanize_scope(
                        scope,
                        ctx=guild
                        if scope == PlaylistScope.GUILD.value
                        else author,
                    ),
                ),
            )

    @command_audioset_guild_autoplay.command(name="reset")
    async def command_audioset_guild_autoplay_reset(
        self, ctx: commands.Context
    ):
        """Resets auto-play to the default playlist."""
        playlist_data = dict(
            enabled=True,
            id=42069,
            name="Aikaterna's curated tracks",
            scope=PlaylistScope.GLOBAL.value,
        )

        await self.config.guild(ctx.guild).autoplaylist.set(playlist_data)
        return await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Set auto-play playlist to play recently played tracks.",
        )

    @command_audioset_guild.command(name="autolyrics")
    async def command_audioset_guild_auto_lyrics(self, ctx: commands.Context):
        """Toggle Lyrics to be shown when a new track starts"""
        auto_lyrics = await self.config_cache.auto_lyrics.get_guild(ctx.guild)
        await self.config_cache.auto_lyrics.set_guild(
            ctx.guild, not auto_lyrics
        )
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Auto Lyrics: {true_or_false}.".format(
                true_or_false=ENABLED_TITLE
                if not auto_lyrics
                else DISABLED_TITLE
            ),
        )

    @command_audioset_guild.command(name="info", aliases=["settings"])
    async def command_audioset_guild_info(self, ctx: commands.Context):
        """Display server settings."""
        empty_dc_enabled = await self.config_cache.empty_dc.get_guild(
            ctx.guild
        )
        empty_dc_timer = await self.config_cache.empty_dc_timer.get_guild(
            ctx.guild
        )
        empty_pause_enabled = await self.config_cache.empty_pause.get_guild(
            ctx.guild
        )
        empty_pause_timer = (
            await self.config_cache.empty_pause_timer.get_guild(ctx.guild)
        )
        jukebox = await self.config_cache.jukebox.get_guild(ctx.guild)
        jukebox_price = await self.config_cache.jukebox_price.get_guild(
            ctx.guild
        )
        disconnect = await self.config_cache.disconnect.get_guild(ctx.guild)
        maxlength = await self.config_cache.max_track_length.get_guild(
            ctx.guild
        )
        persist_queue = await self.config_cache.persistent_queue.get_guild(
            ctx.guild
        )
        auto_deafen = await self.config_cache.auto_deafen.get_guild(ctx.guild)
        lyrics = await self.config_cache.prefer_lyrics.get_guild(ctx.guild)
        restrict = await self.config_cache.url_restrict.get_guild(ctx.guild)
        volume = await self.config_cache.volume.get_guild(ctx.guild)
        thumbnail = await self.config_cache.thumbnail.get_guild(ctx.guild)
        max_queue = await self.config_cache.max_queue_size.get_guild(ctx.guild)
        country_code = await self.config_cache.country_code.get_guild(
            ctx.guild
        )
        daily_playlist = await self.config_cache.daily_playlist.get_guild(
            ctx.guild
        )
        autoplay = await self.config_cache.autoplay.get_guild(ctx.guild)
        dj_roles = await self.config_cache.dj_roles.get_guild(ctx.guild)
        dj_enabled = await self.config_cache.dj_status.get_guild(ctx.guild)
        vote_mode = await self.config_cache.votes.get_guild(ctx.guild)
        vote_percentage = await self.config_cache.votes_percentage.get_guild(
            ctx.guild
        )
        notify = await self.config_cache.notify.get_guild(ctx.guild)
        bumpped_shuffle = await self.config_cache.shuffle_bumped.get_guild(
            ctx.guild
        )
        repeat = await self.config_cache.repeat.get_guild(ctx.guild)
        shuffle = await self.config_cache.shuffle.get_guild(ctx.guild)
        auto_lyrics = await self.config_cache.auto_lyrics.get_guild(ctx.guild)
        autoplaylist = await self.config.guild(ctx.guild).autoplaylist()

        disabled = DISABLED_TITLE
        enabled = ENABLED_TITLE

        msg = "----" + "Server Settings" + "----        \n"
        msg += (
            "DJ mode:             [{dj_mode}]\n"
            "DJ roles:            [{dj_roles}]\n"
            "Vote mode:           [{vote_enabled}]\n"
            "Vote percentage:     [{vote_percent}%]\n"
            "Auto-play:           [{autoplay}]\n"
            "Auto-Lyrics:         [{auto_lyrics}]\n"
            "Auto-disconnect:     [{dc}]\n"
            "Empty dc:            [{empty_dc_enabled}]\n"
            "Empty dc timer:      [{dc_num_seconds}]\n"
            "Empty pause:         [{empty_pause_enabled}]\n"
            "Empty pause timer:   [{pause_num_seconds}]\n"
            "Jukebox:             [{jukebox}]\n"
            "Command price:       [{jukebox_price}]\n"
            "Max track length:    [{tracklength}]\n"
            "Volume:              [{volume}%]\n"
            "URL restrict:        [{restrict}]\n"
            "Prefer lyrics:       [{lyrics}]\n"
            "Song notify msgs:    [{notify}]\n"
            "Persist queue:       [{persist_queue}]\n"
            "Spotify search:      [{countrycode}]\n"
            "Auto-deafen:         [{auto_deafen}]\n"
            "Thumbnails:          [{thumbnail}]\n"
            "Max queue length:    [{max_queue}]\n"
            "Historical playlist: [{historical_playlist}]\n"
            "Repeat:              [{repeat}]\n"
            "Shuffle:             [{shuffle}]\n"
            "Shuffle bumped:      [{bumpped_shuffle}]\n"
        ).format(
            dj_mode=enabled if dj_enabled else disabled,
            dj_roles=len(dj_roles),
            vote_percent=vote_percentage,
            vote_enabled=enabled if vote_mode else disabled,
            autoplay=enabled if autoplay else disabled,
            dc=enabled if disconnect else disabled,
            dc_num_seconds=self.get_time_string(empty_dc_timer),
            empty_pause_enabled=enabled if empty_pause_enabled else disabled,
            empty_dc_enabled=enabled if empty_dc_enabled else disabled,
            pause_num_seconds=self.get_time_string(empty_pause_timer),
            jukebox=jukebox,
            jukebox_price=humanize_number(jukebox_price),
            tracklength=self.get_time_string(maxlength),
            volume=volume,
            restrict=restrict,
            countrycode=country_code,
            persist_queue=persist_queue,
            auto_deafen=auto_deafen,
            thumbnail=enabled if thumbnail else disabled,
            notify=enabled if notify else disabled,
            max_queue=humanize_number(max_queue),
            historical_playlist=enabled if daily_playlist else disabled,
            lyrics=enabled if lyrics else disabled,
            repeat=enabled if repeat else disabled,
            shuffle=enabled if shuffle else disabled,
            bumpped_shuffle=enabled if bumpped_shuffle else disabled,
            auto_lyrics=enabled if auto_lyrics else disabled,
        )

        if autoplaylist["enabled"]:
            pname = autoplaylist["name"]
            pid = autoplaylist["id"]
            pscope = autoplaylist["scope"]
            if pscope == PlaylistScope.GUILD.value:
                pscope = "Server"
            elif pscope == PlaylistScope.USER.value:
                pscope = "User"
            else:
                pscope = "Global"
            msg += (
                "\n---"
                + "Auto-play Settings"
                + "---        \n"
                + "Playlist name:    [{pname}]\n"
                + "Playlist ID:      [{pid}]\n"
                + "Playlist scope:   [{pscope}]\n"
            ).format(pname=pname, pid=pid, pscope=pscope)

        await self.send_embed_msg(
            ctx, description=box(msg, lang="ini"), no_embed=True
        )

    # --------------------------- Lavalink COMMANDS ----------------------------

    @command_audioset.group(
        name="lavalink", aliases=["ll", "llset", "llsetup"]
    )
    @commands.is_owner()
    async def command_audioset_lavalink(self, ctx: commands.Context):
        """Lavalink configuration options."""

    @command_audioset_lavalink.command(name="localpath")
    @commands.bot_has_permissions(add_reactions=True)
    async def command_audioset_lavalink_localpath(
        self, ctx: commands.Context, *, local_path=None
    ):
        """Set the localtracks path if the Lavalink.jar is not run from the Audio data folder.

        Leave the path blank to reset the path to the default, the Audio data directory.
        """

        if not local_path:
            await self.config_cache.localpath.set_global(
                cog_data_path(raw_name="Music")
            )
            self.local_folder_current_path = cog_data_path(raw_name="Music")
            return await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="The localtracks path location has been reset to {localpath}".format(
                    localpath=str(cog_data_path(raw_name="Music").absolute())
                ),
            )

        info_msg = (
            "This setting is only for bot owners to set a localtracks folder location "
            "In the example below, the full path for 'ParentDirectory' "
            "must be passed to this command.\n"
            "```\n"
            "ParentDirectory\n"
            "  |__ localtracks  (folder)\n"
            "  |     |__ Awesome Album Name  (folder)\n"
            "  |           |__01 Cool Song.mp3\n"
            "  |           |__02 Groovy Song.mp3\n"
            "```\n"
            "The folder path given to this command must contain the localtracks folder.\n"
            "**This folder and files need to be visible to the user where `"
            "Lavalink.jar` is being run from.**\n"
            "Use this command with no path given to reset it to the default, "
            "the Music data directory for this bot.\n"
            "Do you want to continue to set the provided path for local tracks?"
        )
        info = await ctx.maybe_send_embed(info_msg)

        start_adding_reactions(info, ReactionPredicate.YES_OR_NO_EMOJIS)
        pred = ReactionPredicate.yes_or_no(info, ctx.author)
        await self.bot.wait_for("reaction_add", check=pred)

        if not pred.result:
            with contextlib.suppress(discord.HTTPException):
                await info.delete()
            return
        temp = LocalPath(
            local_path, self.local_folder_current_path, forced=True
        )
        if not temp.exists() or not temp.is_dir():
            return await self.send_embed_msg(
                ctx,
                title="Invalid Path",
                description="{local_path} does not seem like a valid path.".format(
                    local_path=local_path
                ),
            )

        if not temp.localtrack_folder.exists():
            warn_msg = (
                "`{localtracks}` does not exist. "
                "The path will still be saved, but please check the path and "
                "create a localtracks folder in `{localfolder}` before attempting "
                "to play local tracks."
            ).format(
                localfolder=temp.absolute(),
                localtracks=temp.localtrack_folder.absolute(),
            )
            await self.send_embed_msg(
                ctx, title="Invalid Environment", description=warn_msg
            )
        local_path = str(temp.localtrack_folder.absolute())
        await self.config_cache.localpath.set_global(
            cog_data_path(raw_name="Music")
        )
        self.local_folder_current_path = temp.localtrack_folder.absolute()
        return await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="The localtracks path location has been set to {localpath}".format(
                localpath=local_path
            ),
        )

    @command_audioset_lavalink.command(name="restart")
    async def command_audioset_lavalink_restart(self, ctx: commands.Context):
        """Restarts the node connection."""
        async with ctx.typing():
            await lavalink.close(self.bot)
            if self.player_manager is not None:
                await self.player_manager.shutdown()

            self.lavalink_restart_connect()

            await self.send_embed_msg(
                ctx,
                title="Restarting Lavalink",
                description="It can take a couple of minutes for Lavalink to fully start up.",
            )

    @command_audioset_lavalink.group(name="node")
    async def command_audioset_lavalink_node(self, ctx: commands.Context):
        """Configure node specific settings.

        Note: Currently `node` may only be set to "primary".
        """

    # noinspection HttpUrlsUsage
    @command_audioset_lavalink_node.command(name="host")
    async def command_audioset_lavalink_node_host(
        self, ctx: commands.Context, host: str, node: str = "primary"
    ):
        """Set the node host.

        Note: Currently `node` may only be set to "primary".
        """
        if node not in (
            nodes := await self.config_cache.node_config.get_all_identifiers()
        ):  # TODO: Reenable when LL.py is merged in
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="{node} doesn't exist.\nAvailable nodes: {nodes}.".format(
                    nodes=humanize_list(list(nodes), style="or"), node=node
                ),
            )

        try:
            url = urlparse(host)
        except Exception:
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="`{rest_uri}` is not a valid hostname".format(
                    rest_uri=host
                ),
            )
        if not url.scheme or url.scheme not in ["https", "http"]:
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description=(
                    "`{rest_uri}` is not valid, it must start with `https://` or `http://`"
                ).format(rest_uri=host),
            )
        hostname = url.hostname
        if not hostname:
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="`Unable to retrieve hostname from `{rest_uri}`.".format(
                    rest_uri=host
                ),
            )
        await self.config_cache.node_config.set_host(
            node_identifier=node, set_to=hostname
        )
        if url.port:
            final_port = url.port
            await self.config_cache.node_config.set_port(
                node_identifier=node, set_to=url.port
            )
        else:
            final_port = await self.config_cache.node_config.get_port(
                node_identifier=node
            )

        final_host = f"{url.scheme}://{hostname}"
        if final_port:
            final_uri = f"{final_host}:{final_port}"
        else:
            final_uri = final_host

        await self.config_cache.node_config.set_host(
            node_identifier=node, set_to=final_host
        )
        await self.config_cache.node_config.set_rest_uri(
            node_identifier=node, set_to=final_uri
        )

        footer = None
        if await self.update_external_status():
            footer = "External node set to True."
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description=(
                "URI set to      `{rest_uri}`\n"
                "Hostname set to `{uri_host}`\n"
                "Port set to     `{uri_port}`\n"
            ).format(
                rest_uri=final_uri, uri_port=final_port, uri_host=final_host
            ),
            footer=footer,
        )
        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title="Failed To Shutdown Lavalink",
                description="Please reload Music (`{prefix}reload audio`).".format(
                    prefix=ctx.prefix
                ),
            )

    @command_audioset_lavalink_node.command(
        name="token", aliases=["password", "pass"]
    )
    async def command_audioset_lavalink_node_password(
        self, ctx: commands.Context, password: str, node: str = "primary"
    ):
        """Set the node authentication password."""

        if node not in (
            nodes := await self.config_cache.node_config.get_all_identifiers()
        ):
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="{node} doesn't exist.\nAvailable nodes: {nodes}.".format(
                    nodes=humanize_list(list(nodes), style="or"), node=node
                ),
            )
        await self.config_cache.node_config.set_password(
            node_identifier=node, set_to=password
        )

        footer = None
        if await self.update_external_status():
            footer = "External node set to True."
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Server password set to {password}.".format(
                password=password
            ),
            footer=footer,
        )

        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title="Failed To Shutdown Lavalink",
                description="Please reload Music (`{prefix}reload audio`).".format(
                    prefix=ctx.prefix
                ),
            )

    @command_audioset_lavalink_node.command(name="port")
    async def command_audioset_lavalink_node_port(
        self, ctx: commands.Context, port: int, node: str = "primary"
    ):
        """Set the node websocket port for the node."""
        if node not in (
            nodes := await self.config_cache.node_config.get_all_identifiers()
        ):
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="{node} doesn't exist.\nAvailable nodes: {nodes}.".format(
                    nodes=humanize_list(list(nodes), style="or"), node=node
                ),
            )
        await self.config_cache.node_config.set_port(
            node_identifier=node, set_to=port
        )
        rest_uri = await self.config_cache.node_config.get_rest_uri(
            node_identifier=node
        )
        url = urlparse(rest_uri)
        rest_uri = f"{url.scheme}://{url.hostname}:{port}"

        await self.config_cache.node_config.set_rest_uri(
            node_identifier=node, set_to=rest_uri
        )
        uri_host = await self.config_cache.node_config.get_host(
            node_identifier=node
        )

        footer = None
        if await self.update_external_status():
            footer = "External node set to True."
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description=(
                "URI set to      `{rest_uri}`\n"
                "Hostname set to `{uri_host}`\n"
                "Port set to     `{uri_port}`\n"
            ).format(rest_uri=rest_uri, uri_port=port, uri_host=uri_host),
            footer=footer,
        )

        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title="Failed To Shutdown Lavalink",
                description="Please reload Music (`{prefix}reload audio`).".format(
                    prefix=ctx.prefix
                ),
            )

    @command_audioset_lavalink_node.command(name="uri")
    async def command_audioset_lavalink_node_uri(
        self,
        ctx: commands.Context,
        rest_uri: str = None,
        node: str = "primary",
    ):
        """Set the Rest URI for the node."""
        if node not in (
            nodes := await self.config_cache.node_config.get_all_identifiers()
        ):
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="{node} doesn't exist.\nAvailable nodes: {nodes}.".format(
                    nodes=humanize_list(list(nodes), style="or"), node=node
                ),
            )
        try:
            url = urlparse(rest_uri)
        except Exception:
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="`{rest_uri}` is not a valid hostname".format(
                    rest_uri=rest_uri
                ),
            )
        if not url.scheme or url.scheme not in ["https", "http"]:
            # noinspection HttpUrlsUsage
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description=(
                    "`{rest_uri}` is not valid, it must start with `https://` or `http://`"
                ).format(rest_uri=rest_uri),
            )
        await self.config_cache.node_config.set_rest_uri(
            node_identifier=node, set_to=rest_uri
        )
        rest_uri = await self.config_cache.node_config.get_rest_uri(
            node_identifier=node
        )
        url = urlparse(rest_uri)
        if url.port:
            await self.config_cache.node_config.set_port(
                node_identifier=node, set_to=url.port
            )
        else:
            await self.config_cache.node_config.set_port(
                node_identifier=node, set_to=None
            )
        if url.hostname:
            await self.config_cache.node_config.set_host(
                node_identifier=node, set_to=f"{url.scheme}://{url.hostname}"
            )

        uri_host = await self.config_cache.node_config.get_host(
            node_identifier=node
        )
        uri_port = await self.config_cache.node_config.get_port(
            node_identifier=node
        )

        footer = None
        if await self.update_external_status():
            footer = "External node set to True."
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description=(
                "URI set to      `{rest_uri}`\n"
                "Hostname set to `{uri_host}`\n"
                "Port set to     `{uri_port}`\n"
            ).format(rest_uri=rest_uri, uri_port=uri_port, uri_host=uri_host),
            footer=footer,
        )

        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title="Failed To Shutdown Lavalink",
                description="Please reload Music (`{prefix}reload audio`).".format(
                    prefix=ctx.prefix
                ),
            )

    @command_audioset_lavalink_node.command(
        name="region", enabled=False
    )  # TODO: Reenable when LL.py is merged in
    async def command_audioset_lavalink_node_region(
        self, ctx: commands.Context, region: str = None, node: str = "primary"
    ):
        """Set the Discord voice region for the node."""
        if node not in (
            nodes := await self.config_cache.node_config.get_all_identifiers()
        ):
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="{node} doesn't exist.\nAvailable nodes: {nodes}.".format(
                    nodes=humanize_list(list(nodes), style="or"), node=node
                ),
            )
        await self.config_cache.node_config.set_region(
            node_identifier=node, set_to=region
        )
        region = await self.config_cache.node_config.get_region(
            node_identifier=node
        )

        footer = None
        if await self.update_external_status():
            footer = "External node set to True."
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Node will now serve the following region: {region}.".format(
                region=region if region else "all"
            ),
            footer=footer,
        )

        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title="Failed To Shutdown Lavalink",
                description="Please reload Music (`{prefix}reload audio`).".format(
                    prefix=ctx.prefix
                ),
            )

    @command_audioset_lavalink_node.command(
        name="shard", enabled=False
    )  # TODO: Reenable when LL.py is merged in
    async def command_audioset_lavalink_node_shard(
        self,
        ctx: commands.Context,
        shard_id: str = None,
        node: str = "primary",
    ):
        """Set the Discord voice region for the node."""
        if node not in (
            nodes := await self.config_cache.node_config.get_all_identifiers()
        ):
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="{node} doesn't exist.\nAvailable nodes: {nodes}.".format(
                    nodes=humanize_list(list(nodes), style="or"), node=node
                ),
            )
        await self.config_cache.node_config.set_shard_id(
            node_identifier=node, set_to=shard_id
        )
        shard_id = await self.config_cache.node_config.get_shard_id(
            node_identifier=node
        )
        footer = None
        if await self.update_external_status():
            footer = "External node set to True."
        if shard_id != -1:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Node will now only serve shard: {shard_id}.".format(
                    shard_id=shard_id
                ),
                footer=footer,
            )
        else:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Node will now serve all shards.",
                footer=footer,
            )

        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title="Failed To Shutdown Lavalink",
                description="Please reload Music (`{prefix}reload audio`).".format(
                    prefix=ctx.prefix
                ),
            )

    @command_audioset_lavalink_node.command(
        name="search", enabled=False
    )  # TODO: Reenable when LL.py is merged in
    async def command_audioset_lavalink_node_search(
        self, ctx: commands.Context, node: str = "primary"
    ):
        """Toggle a node to only service searches."""
        if node not in (
            nodes := await self.config_cache.node_config.get_all_identifiers()
        ):
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="{node} doesn't exist.\nAvailable nodes: {nodes}.".format(
                    nodes=humanize_list(list(nodes), style="or"), node=node
                ),
            )
        state = await self.config_cache.node_config.get_search_only(
            node_identifier=node
        )
        await self.config_cache.node_config.set_search_only(
            node_identifier=node, set_to=not state
        )
        footer = None
        if await self.update_external_status():
            footer = "External node set to True."
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Search only: {shard_id}.".format(
                shard_id=ENABLED_TITLE if not state else DISABLED_TITLE
            ),
            footer=footer,
        )

        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title="Failed To Shutdown Lavalink",
                description="Please reload Music (`{prefix}reload audio`).".format(
                    prefix=ctx.prefix
                ),
            )

    @command_audioset_lavalink.group(
        name="managed", aliases=["external", "internal"]
    )
    async def command_audioset_lavalink_managed(self, ctx: commands.Context):
        """Change settings for the managed node."""

    @command_audioset_lavalink_managed.command(name="logs")
    async def command_audioset_lavalink_logs(self, ctx: commands.Context):
        """Sends the managed node logs to your DMs."""
        if not await self.config_cache.use_managed_lavalink.get_context_value(
            ctx.guild
        ):
            return await self.send_embed_msg(
                ctx,
                title="Invalid Environment",
                description=(
                    "You cannot changed the Java executable path of "
                    "external Lavalink instances from the Music Cog."
                ),
            )

        datapath = cog_data_path(raw_name="Music")
        logs = datapath / "logs" / "spring.log"
        zip_name = None
        try:
            try:
                if not (logs.exists() and logs.is_file()):
                    return await ctx.send("No logs found in your data folder.")
            except OSError:
                return await ctx.send("No logs found in your data folder.")

            def check(path):
                return os.path.getsize(str(path)) > (8388608 - 1000)

            if check(logs):
                zip_name = logs.with_suffix(".tar.gz")
                zip_name.unlink(missing_ok=True)
                with tarfile.open(zip_name, "w:gz") as tar:
                    tar.add(str(logs), arcname="spring.log", recursive=False)
                if check(zip_name):
                    await ctx.send(
                        "Logs are too large, you can find them in {path}".format(
                            path=zip_name.absolute()
                        )
                    )
                    zip_name = None
                else:
                    await ctx.author.send(file=discord.File(str(zip_name)))
            else:
                await ctx.author.send(file=discord.File(str(logs)))
        except discord.HTTPException:
            await ctx.send("I need to be able to DM you to send you the logs.")
        finally:
            if zip_name is not None:
                zip_name.unlink(missing_ok=True)

    @command_audioset_lavalink_managed.command(name="java")
    async def command_audioset_lavalink_java(
        self, ctx: commands.Context, *, java_path: str = None
    ):
        """Change your Java executable path

        Enter nothing to reset to default.
        """
        internal = (
            await self.config_cache.use_managed_lavalink.get_context_value(
                ctx.guild
            )
        )
        if not internal:
            return await self.send_embed_msg(
                ctx,
                title="Invalid Environment",
                description=(
                    "You cannot changed the Java executable path of "
                    "external Lavalink instances from the Music Cog."
                ),
            )
        if java_path is None:
            await self.config_cache.java_exec.set_global(None)
            await self.send_embed_msg(
                ctx,
                title="Java Executable Reset",
                description="Music will now use `java` to run your Lavalink.jar",
            )
        else:
            exc = Path(java_path)
            exc_absolute = exc.absolute()
            if not exc.exists() or not exc.is_file():
                return await self.send_embed_msg(
                    ctx,
                    title="Invalid Environment",
                    description="`{java_path}` is not a valid executable".format(
                        java_path=exc_absolute
                    ),
                )
            await self.config_cache.java_exec.set_global(exc_absolute)
            await self.send_embed_msg(
                ctx,
                title="Java Executable Changed",
                description="Music will now use `{exc}` to run your Lavalink.jar".format(
                    exc=exc_absolute
                ),
            )
        try:
            if self.player_manager is not None:
                await self.player_manager.shutdown()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title="Failed To Shutdown Lavalink",
                description=(
                    "For it to take effect please reload Music (`{prefix}reload audio`)."
                ).format(
                    prefix=ctx.prefix,
                ),
            )
        else:
            try:
                self.lavalink_restart_connect()
            except ProcessLookupError:
                await self.send_embed_msg(
                    ctx,
                    title="Failed To Shutdown Lavalink",
                    description="Please reload Audio (`{prefix}reload audio`).".format(
                        prefix=ctx.prefix
                    ),
                )

    @command_audioset_lavalink_managed.command(name="toggle")
    async def command_audioset_lavalink_managed_toggle(
        self, ctx: commands.Context
    ):
        """Toggle using external nodes servers."""
        managed = (
            await self.config_cache.use_managed_lavalink.get_context_value(
                ctx.guild
            )
        )
        await self.config_cache.use_managed_lavalink.set_global(not managed)

        if not managed:
            embed = discord.Embed(
                title="Setting Changed",
                description="Managed node: {true_or_false}.".format(
                    true_or_false=ENABLED_TITLE
                    if not managed
                    else DISABLED_TITLE
                ),
            )
            await self.send_embed_msg(ctx, embed=embed)
        else:
            try:
                if self.player_manager is not None:
                    await self.player_manager.shutdown()
            except ProcessLookupError:
                await self.send_embed_msg(
                    ctx,
                    title="Failed To Shutdown Lavalink",
                    description=(
                        "Managed node: {true_or_false}\n"
                        "For it to take effect please reload "
                        "Audio (`{prefix}reload audio`)."
                    ).format(
                        true_or_false=ENABLED_TITLE
                        if not managed
                        else DISABLED_TITLE,
                        prefix=ctx.prefix,
                    ),
                )
            else:
                await self.send_embed_msg(
                    ctx,
                    title="Setting Changed",
                    description="Managed node: {true_or_false}.".format(
                        true_or_false=ENABLED_TITLE
                        if not managed
                        else DISABLED_TITLE
                    ),
                )
        try:
            self.lavalink_restart_connect()
        except ProcessLookupError:
            await self.send_embed_msg(
                ctx,
                title="Failed To Shutdown Lavalink",
                description="Please reload Audio (`{prefix}reload audio`).".format(
                    prefix=ctx.prefix
                ),
            )

    @command_audioset_lavalink_managed.group(name="downloader", aliases=["dl"])
    async def command_audioset_lavalink_managed_downloader(
        self, ctx: commands.Context
    ):
        """Configure the managed Lavalink downloading options."""

    @command_audioset_lavalink_managed_downloader.command(name="build")
    async def command_audioset_lavalink_managed_downloader_build(
        self, ctx: commands.Context, build: int = None
    ):
        """Set the build ID to check against when downloading the JAR.

        Note if you set this, we will download this version and will not keep it up to date.

        **Warning**: Setting anything here will void any support provided by Red.
        """
        if not await self.config_cache.use_managed_lavalink.get_global():
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="You are only able to set this if you are running a managed node.",
            )
        await self.config_cache.managed_lavalink_meta.set_global_build(build)
        if build:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Lavalink downloader will get build: {build}.".format(
                    build=build
                ),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Lavalink downloader attempt to get the latest known version.",
            )

    @command_audioset_lavalink_managed_downloader.command(name="url")
    async def command_audioset_lavalink_managed_downloader_url(
        self, ctx: commands.Context, url: str = None
    ):
        """Set the **direct** URL to download the JAR from.

        Note if you set this, we will download this version and will not keep it up to date.

        **Warning**: Setting anything here will void any support provided by Red.
        """
        if not await self.config_cache.use_managed_lavalink.get_global():
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="You are only able to set this if you are running a node.",
            )
        await self.config_cache.managed_lavalink_meta.set_global_build(url)
        if url:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Lavalink downloader will get the following jar: <{url}>.".format(
                    url=url
                ),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Lavalink downloader attempt to get the latest known version.",
            )

    @command_audioset_lavalink_managed.group(
        name="config", aliases=["conf", "yaml"]
    )
    async def command_audioset_lavalink_managed_config(
        self, ctx: commands.Context
    ):
        """Configure the local node runtime options."""

    @command_audioset_lavalink_managed_config.group(name="server")
    async def command_audioset_lavalink_managed_config_server(
        self, ctx: commands.Context
    ):
        """Configure the Server authorization and connection settings."""

    @command_audioset_lavalink_managed_config_server.command(name="host")
    async def command_audioset_lavalink_managed_config_server_host(
        self, ctx: commands.Context, host: str = None
    ):
        """Set the server host address.

        Default is: "localhost"
        """
        if not await self.config_cache.use_managed_lavalink.get_global():
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="You are only able to set this if you are running a managed node.",
            )

        await self.config_cache.managed_lavalink_yaml.set_server_address(
            set_to=host
        )
        host = (
            await self.config_cache.managed_lavalink_yaml.get_server_address()
        )
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description=(
                "Managed node will now accept connection on {host}.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(
                host=host,
                p=ctx.prefix,
                cmd=self.command_audioset_lavalink_restart.qualified_name,
            ),
        )

    @command_audioset_lavalink_managed_config_server.command(
        name="token", aliases=["password", "pass"]
    )
    async def command_audioset_lavalink_managed_config_server_token(
        self, ctx: commands.Context, password: str = None
    ):
        """Set the server authorization token.

        Default is: "youshallnotpass"
        """
        if not await self.config_cache.use_managed_lavalink.get_global():
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="You are only able to set this if you are running a managed node.",
            )

        await self.config_cache.managed_lavalink_yaml.set_lavalink_password(
            set_to=password
        )
        password = (
            await self.config_cache.managed_lavalink_yaml.get_lavalink_password()
        )
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description=(
                "Managed node will now accept {password} as the authorization token.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(
                password=password,
                p=ctx.prefix,
                cmd=self.command_audioset_lavalink_restart.qualified_name,
            ),
        )

    @command_audioset_lavalink_managed_config_server.command(name="port")
    async def command_audioset_lavalink_managed_config_server_port(
        self, ctx: commands.Context, port: int = None
    ):
        """Set the server connection port.

        Default is: "2333"
        """
        if not await self.config_cache.use_managed_lavalink.get_global():
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="You are only able to set this if you are running a managed node.",
            )

        await self.config_cache.managed_lavalink_yaml.set_server_port(
            set_to=port
        )
        port = await self.config_cache.managed_lavalink_yaml.get_server_port()
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description=(
                "Managed node will now accept connection on {port}.\n\n"
                "Run `{p}{cmd}` for it to take effect."
            ).format(
                port=port,
                p=ctx.prefix,
                cmd=self.command_audioset_lavalink_restart.qualified_name,
            ),
        )

    @command_audioset_lavalink_managed_config_server.command(
        name="jdanas", aliases=["jda"]
    )
    async def command_audioset_lavalink_managed_config_server_jdanas(
        self, ctx: commands.Context
    ):
        """Toggle JDA-NAS on or off."""
        if not await self.config_cache.use_managed_lavalink.get_global():
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="You are only able to set this if you are running a managed node.",
            )

        state = await self.config_cache.managed_lavalink_yaml.get_jda_nsa()
        await self.config_cache.managed_lavalink_yaml.set_jda_nsa(not state)
        if not state:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node will now start with JDA-NAS enabled.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_lavalink_restart.qualified_name,
                ),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node will now start with JDA-NAS disabled.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_lavalink_restart.qualified_name,
                ),
            )

    @command_audioset_lavalink_managed_config.group(name="source")
    async def command_audioset_lavalink_managed_config_source(
        self, ctx: commands.Context
    ):
        """Toggle audio sources on/off."""

    @command_audioset_lavalink_managed_config_source.command(name="http")
    async def command_audioset_lavalink_managed_config_source_http(
        self, ctx: commands.Context
    ):
        """Toggle HTTP direct URL usage on or off."""
        if not await self.config_cache.use_managed_lavalink.get_global():
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="You are only able to set this if you are running a managed node.",
            )

        state = await self.config_cache.managed_lavalink_yaml.get_source_http()
        await self.config_cache.managed_lavalink_yaml.set_source_http(
            not state
        )
        if not state:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node will allow playback from direct URLs.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_lavalink_restart.qualified_name,
                ),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node will not play from direct URLs anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_lavalink_restart.qualified_name,
                ),
            )

    @command_audioset_lavalink_managed_config_source.command(
        name="bandcamp", aliases=["bc"]
    )
    async def command_audioset_lavalink_managed_config_source_bandcamp(
        self, ctx: commands.Context
    ):
        """Toggle Bandcamp source on or off."""
        if not await self.config_cache.use_managed_lavalink.get_global():
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="You are only able to set this if you are running a managed node.",
            )

        state = (
            await self.config_cache.managed_lavalink_yaml.get_source_bandcamp()
        )
        await self.config_cache.managed_lavalink_yaml.set_source_bandcamp(
            not state
        )
        if not state:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node will allow playback from Bandcamp.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_lavalink_restart.qualified_name,
                ),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node will not play from Bandcamp anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_lavalink_restart.qualified_name,
                ),
            )

    @command_audioset_lavalink_managed_config_source.command(name="local")
    async def command_audioset_lavalink_managed_config_source_local(
        self, ctx: commands.Context
    ):
        """Toggle local file usage on or off."""
        if not await self.config_cache.use_managed_lavalink.get_global():
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="You are only able to set this if you are running a managed node.",
            )

        state = (
            await self.config_cache.managed_lavalink_yaml.get_source_local()
        )
        await self.config_cache.managed_lavalink_yaml.set_source_local(
            not state
        )
        if not state:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node will allow playback from local files.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_lavalink_restart.qualified_name,
                ),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node will not play from local files anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_lavalink_restart.qualified_name,
                ),
            )

    @command_audioset_lavalink_managed_config_source.command(
        name="soundcloud", aliases=["sc"]
    )
    async def command_audioset_lavalink_managed_config_source_soundcloud(
        self, ctx: commands.Context
    ):
        """Toggle Soundcloud source on or off."""
        if not await self.config_cache.use_managed_lavalink.get_global():
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="You are only able to set this if you are running a managed node.",
            )

        state = (
            await self.config_cache.managed_lavalink_yaml.get_source_soundcloud()
        )
        await self.config_cache.managed_lavalink_yaml.set_source_soundcloud(
            not state
        )
        if not state:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node will allow playback from Soundcloud.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_lavalink_restart.qualified_name,
                ),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node will not play from Soundcloud anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_lavalink_restart.qualified_name,
                ),
            )

    @command_audioset_lavalink_managed_config_source.command(
        name="youtube", aliases=["yt"]
    )
    async def command_audioset_lavalink_managed_config_source_youtube(
        self, ctx: commands.Context
    ):
        """Toggle YouTube source on or off."""
        if not await self.config_cache.use_managed_lavalink.get_global():
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="You are only able to set this if you are running a managed node.",
            )

        state = (
            await self.config_cache.managed_lavalink_yaml.get_source_youtube()
        )
        await self.config_cache.managed_lavalink_yaml.set_source_youtube(
            not state
        )
        if not state:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node will allow playback from YouTube.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_lavalink_restart.qualified_name,
                ),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node will not play from YouTube anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_lavalink_restart.qualified_name,
                ),
            )

    @command_audioset_lavalink_managed_config_source.command(name="twitch")
    async def command_audioset_lavalink_managed_config_source_twitch(
        self, ctx: commands.Context
    ):
        """Toggle Twitch source on or off."""
        if not await self.config_cache.use_managed_lavalink.get_global():
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="You are only able to set this if you are running a managed node.",
            )

        state = (
            await self.config_cache.managed_lavalink_yaml.get_source_twitch()
        )
        await self.config_cache.managed_lavalink_yaml.set_source_twitch(
            not state
        )
        if not state:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node will allow playback from Twitch.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_lavalink_restart.qualified_name,
                ),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node will not play from Twitch anymore.\n\n"
                    "Run `{p}{cmd}` for it to take effect."
                ).format(
                    p=ctx.prefix,
                    cmd=self.command_audioset_lavalink_restart.qualified_name,
                ),
            )

    @command_audioset_lavalink_managed_downloader.command(name="stable")
    async def command_audioset_lavalink_managed_downloader_stable(
        self, ctx: commands.Context
    ):
        """Toggle between the pre-release track and the stable track.

        Note This only takes affect if auto-update is enabled and you have not set a URL/Build number.

        **Warning**: Using the pre-release track will void any support provided by Red.
        """
        if not await self.config_cache.use_managed_lavalink.get_global():
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="You are only able to set this if you are running a managed node.",
            )
        state = (
            await self.config_cache.managed_lavalink_meta.get_global_stable()
        )
        await self.config_cache.managed_lavalink_meta.set_global_stable(
            not state
        )

        if not state:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Managed node downloader will use the stable track for JARs.",
            )
        else:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description="Managed node downloader will use the pre-release track for JARs.",
            )

    @command_audioset_lavalink_managed_downloader.command(name="update")
    async def command_audioset_lavalink_managed_downloader_update(
        self, ctx: commands.Context
    ):
        """Toggle between the auto-update functionality."""
        if not await self.config_cache.use_managed_lavalink.get_global():
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="You are only able to set this if you are running a managed node.",
            )
        state = (
            await self.config_cache.managed_lavalink_server_auto_update.get_global()
        )
        await self.config_cache.managed_lavalink_server_auto_update.set_global(
            not state
        )

        if not state:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node downloader will now auto-update upon cog reload and bot restart."
                ),
            )
        else:
            await self.send_embed_msg(
                ctx,
                title="Setting Changed",
                description=(
                    "Managed node downloader will no longer auto-update and will depend on Red version updates."
                ),
            )

    @command_audioset_lavalink_managed_downloader.command(name="check")
    async def command_audioset_lavalink_managed_downloader_check(
        self, ctx: commands.Context
    ):
        """See the latest version of Red's Lavalink server."""

        name, tag, url, date = await get_latest_lavalink_release(date=True)
        version, build = tag.split("_")
        msg = "----" + "Release Builds" + "----        \n"
        msg += "Release Version:  [{version}]\n".format(version=version)
        msg += "Release Build:    [{build}]\n".format(build=build)
        msg += "Release Date:     [{published}]\n".format(published=date)
        msg += "Release URL:      [{url}]\n\n".format(url=url)

        if await self.config_cache.managed_lavalink_meta.get_global_stable():
            with contextlib.suppress(Exception):
                (
                    alpha_name,
                    alpha_tag,
                    alpha_url,
                    alpha_date,
                ) = await get_latest_lavalink_release(False, date=True)
                alpha_version, alpha_build = alpha_tag.split("_")
                if int(alpha_build) > int(build):
                    msg += "----" + "Alpha Builds" + "----        \n"
                    msg += "Alpha Version:  [{version}]\n".format(
                        version=alpha_version
                    )
                    msg += "Alpha Build:    [{build}]\n".format(
                        build=alpha_build
                    )
                    msg += "Alpha Date:     [{published}]\n".format(
                        published=alpha_date
                    )
                    msg += "Alpha URL:      [{url}]\n\n".format(url=alpha_url)

        await self.send_embed_msg(
            ctx, description=box(msg, lang="ini"), no_embed=True
        )

    @command_audioset_lavalink.command(name="info", aliases=["settings"])
    async def command_audioset_lavalink_info(
        self, ctx: commands.Context, node: str = "primary"
    ):
        """Display node settings."""
        if node not in (
            nodes := await self.config_cache.node_config.get_all_identifiers()
        ):
            return await self.send_embed_msg(
                ctx,
                title="Setting Not Changed",
                description="{node} doesn't exist.\nAvailable nodes: {nodes}.".format(
                    nodes=humanize_list(list(nodes), style="or"), node=node
                ),
            )
        node_obj = lavalink.fetch_node(name=node)
        managed = await self.config_cache.use_managed_lavalink.get_global()
        local_path = await self.config_cache.localpath.get_global()
        host = await self.config_cache.node_config.get_host(
            node_identifier=node
        )
        password = await self.config_cache.node_config.get_password(
            node_identifier=node
        )
        port = await self.config_cache.node_config.get_port(
            node_identifier=node
        )
        rest_uri = await self.config_cache.node_config.get_rest_uri(
            node_identifier=node
        )
        region = await self.config_cache.node_config.get_region(
            node_identifier=node
        )
        shard = await self.config_cache.node_config.get_shard_id(
            node_identifier=node
        )
        search_only = await self.config_cache.node_config.get_search_only(
            node_identifier=node
        )

        msg = "----" + "Connection Settings" + "----        \n"
        msg += "Host:                   [{host}]\n".format(host=host)
        msg += "Port:                   [{port}]\n".format(port=port)
        msg += "Password:               [{password}]\n".format(
            password=password
        )
        msg += "Dedicated shard:        [{shard}]\n".format(
            shard=shard if shard >= 0 else "All"
        )
        msg += "Region:                 [{region}]\n".format(
            region=region if region else "All"
        )
        msg += "Rest URI:               [{rest_uri}]\n".format(
            rest_uri=rest_uri
        )
        msg += "Search Mode:            [{search}]\n".format(
            search=ENABLED_TITLE if search_only else DISABLED_TITLE
        )

        msg += (
            "\n---"
            + "Lavalink Settings"
            + "---        \n"
            + "Cog version:            [{version}]\n"
            + "Red-Lavalink:           [{lavalink_version}]\n"
            + "Managed Lavalink:       [{managed}]\n"
        ).format(
            version=__version__,
            lavalink_version=lavalink.__version__,
            managed=ENABLED_TITLE if managed else DISABLED_TITLE,
        )
        msg += "\n----" + "Node Info" + "----        \n"
        _unknown = "Unknown"
        if node_obj:
            try:
                node_info = await node_obj.server_metadata()
                build_time = node_info.get(
                    "buildTime",
                    self.player_manager.path
                    if self.player_manager and self.player_manager.path
                    else _unknown,
                )
                llbuild = node_info.get(
                    "build",
                    self.player_manager.path
                    if self.player_manager and self.player_manager.path
                    else _unknown,
                )
                llversion = node_info.get("version", _unknown)
                llbranch = node_info.get(
                    "branch",
                    self.player_manager.path
                    if self.player_manager and self.player_manager.path
                    else _unknown,
                )
                lavaplayer = node_info.get(
                    "lavaplayer",
                    self.player_manager.path
                    if self.player_manager and self.player_manager.path
                    else _unknown,
                )
                jvm = node_info.get(
                    "jvm",
                    self.player_manager.path
                    if self.player_manager and self.player_manager.path
                    else _unknown,
                )
                jv_exec = node_info.get(
                    "java_exec",
                    self.player_manager.path
                    if self.player_manager and self.player_manager.path
                    else _unknown,
                )

                msg += (
                    "Build:                  [{llbuild}]\n"
                    "Version:                [{llversion}]\n"
                    "Branch:                 [{llbranch}]\n"
                    "Release date:           [{build_time}]\n"
                    "Lavaplayer:             [{lavaplayer}]\n"
                    "Java version:           [{jvm}]\n"
                    "Java executable:        [{jv_exec}]\n"
                ).format(
                    build_time=build_time,
                    llversion=llversion,
                    llbuild=llbuild,
                    llbranch=llbranch,
                    lavaplayer=lavaplayer,
                    jvm=jvm,
                    jv_exec=jv_exec,
                )
            except Exception:
                pass
        if managed:
            msg += "Lavalink auto-update:   [{update}]\n".format(
                update=await self.config_cache.managed_lavalink_server_auto_update.get_global(),
            )

            custom_url = (
                await self.config_cache.managed_lavalink_meta.get_global_url()
            )
            if custom_url:
                msg += (
                    "Lavalink build:         [{build}]\nLavalink URL:           [{url}]\n"
                ).format(
                    build=await self.config_cache.managed_lavalink_meta.get_global_build(),
                    url=custom_url,
                )
            else:
                if (
                    await self.config_cache.managed_lavalink_meta.get_global_stable()
                ):
                    user_friendly = "Stable"
                else:
                    user_friendly = "Alpha"
                msg += "Download track:         [{track}]\n".format(
                    track=user_friendly,
                )

        msg += "\n----" + "Miscellaneous Settings" + "----        \n"
        msg += "Localtracks path:       [{localpath}]\n".format(
            localpath=local_path
        )

        try:
            await self.send_embed_msg(
                ctx.author, description=box(msg, lang="ini"), no_embed=True
            )
        except discord.HTTPException:
            await ctx.send(
                "I need to be able to DM you to send you this info."
            )

    @command_audioset_lavalink.command(name="stats")
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def command_audioset_lavalink_stats(self, ctx: commands.Context):
        """Show audio stats."""
        server_num = len(lavalink.active_players())
        total_num = len(lavalink.all_connected_players())

        msg = ""
        async for p in AsyncIter(lavalink.all_connected_players()):
            connect_dur = (
                self.get_time_string(
                    int(
                        (
                            datetime.datetime.now(datetime.timezone.utc)
                            - p.connected_at
                        ).total_seconds()
                    )
                )
                or "0s"
            )
            try:
                if not p.current:
                    raise AttributeError
                current_title = await self.get_track_description(
                    p.current, self.local_folder_current_path
                )
                msg += f"{p.guild.name} [`{connect_dur}`]: {current_title}\n"
            except AttributeError:
                msg += "{} [`{}`]: **{}**\n".format(
                    p.guild.name, connect_dur, "Nothing playing."
                )

        if total_num == 0:
            return await self.send_embed_msg(
                ctx, title="Not connected anywhere."
            )
        servers_embed = []
        pages = 1
        for page in pagify(msg, delims=["\n"], page_length=1500):
            em = discord.Embed(
                colour=await ctx.embed_colour(),
                title="Playing in {num}/{total} servers:".format(
                    num=humanize_number(server_num),
                    total=humanize_number(total_num),
                ),
                description=page,
            )
            em.set_footer(
                text="Page {}/{}".format(
                    humanize_number(pages),
                    humanize_number((math.ceil(len(msg) / 1500))),
                )
            )
            pages += 1
            servers_embed.append(em)

        await menu(ctx, servers_embed, DEFAULT_CONTROLS)

    @command_audioset_lavalink.group(name="disconnect", aliases=["dc", "kill"])
    async def command_audioset_lavalink_disconnect(
        self, ctx: commands.Context
    ):
        """Disconnect players."""

    @command_audioset_lavalink_disconnect.command(name="all")
    async def command_audioset_lavalink_disconnect_all(
        self, ctx: commands.Context
    ):
        """Disconnect all players."""
        for player in lavalink.all_players():
            await player.disconnect()
            await self.config_cache.autoplay.set_currently_in_guild(
                player.guild
            )
            await self.api_interface.persistent_queue_api.drop(player.guild.id)
        return await self.send_embed_msg(
            ctx,
            title="Admin Action.",
            description="Successfully disconnected from all voice channels.",
        )

    @command_audioset_lavalink_disconnect.command(name="active")
    async def command_audioset_lavalink_disconnect_active(
        self, ctx: commands.Context
    ):
        """Disconnect all active players."""
        active_players = [
            p for p in lavalink.all_connected_players() if p.current
        ]

        for player in active_players:
            await player.disconnect()
            await self.config_cache.autoplay.set_currently_in_guild(
                player.guild
            )
            await self.api_interface.persistent_queue_api.drop(player.guild.id)
        return await self.send_embed_msg(
            ctx,
            title="Admin Action.",
            description="Successfully disconnected from all active voice channels.",
        )

    @command_audioset_lavalink_disconnect.command(name="idle")
    async def command_audioset_lavalink_disconnect_idle(
        self, ctx: commands.Context
    ):
        """Disconnect all idle players."""
        idle_players = [
            p
            for p in lavalink.all_connected_players()
            if not (p.is_playing or p.is_auto_playing)
        ]
        for player in idle_players:
            await player.disconnect()
            await self.config_cache.autoplay.set_currently_in_guild(
                player.guild
            )
            await self.api_interface.persistent_queue_api.drop(player.guild.id)
        return await self.send_embed_msg(
            ctx,
            title="Admin Action.",
            description="Successfully disconnected from all idle voice channels.",
        )

    @command_audioset_lavalink_disconnect.command(
        name="specific", aliases=["this"]
    )
    async def command_audioset_lavalink_disconnect_specific(
        self, ctx: commands.Context, guild: Union[discord.Guild, int]
    ):
        """Disconnect the specified player."""
        try:
            player = lavalink.get_player(
                guild if type(guild) == int else guild.id
            )
        except (KeyError, IndexError, AttributeError):
            return await self.send_embed_msg(
                ctx,
                title="Player Not Found.",
                description=(
                    "The specified player was not found ensure to provide the correct server ID.."
                ),
            )
        await player.disconnect()
        await self.config_cache.autoplay.set_currently_in_guild(player.guild)
        await self.api_interface.persistent_queue_api.drop(player.guild.id)
        return await self.send_embed_msg(
            ctx,
            title="Admin Action.",
            description="Successfully disconnected from the specified server.",
        )

    # --------------------------- USER COMMANDS ----------------------------
    @command_audioset.group(name="user", aliases=["self", "my", "mine"])
    async def command_audioset_user(self, ctx: commands.Context):
        """User configuration options."""

    @command_audioset_user.command(name="countrycode")
    async def command_audioset_user_countrycode(
        self, ctx: commands.Context, country: str
    ):
        """Set the country code for Spotify searches."""
        if len(country) != 2:
            return await self.send_embed_msg(
                ctx,
                title="Invalid Country Code",
                description=(
                    "Please use an official [ISO 3166-1 alpha-2]"
                    "(https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code."
                ),
            )
        country = country.upper()
        await self.send_embed_msg(
            ctx,
            title="Setting Changed",
            description="Country Code set to {country}.".format(
                country=country
            ),
        )

        await self.config_cache.country_code.set_user(ctx.author, country)

    @command_audioset_user.command(name="info", aliases=["settings", "config"])
    async def command_audioset_user_settings(self, ctx: commands.Context):
        """Show the settings for the user who runs it."""

        country_code = await self.config_cache.country_code.get_user(
            ctx.author
        )
        msg = (
            "----"
            + "User Settings"
            + "----        \nSpotify search:   [{country_code}]\n".format(
                country_code=country_code or "Not set"
            )
        )

        await self.send_embed_msg(
            ctx, description=box(msg, lang="ini"), no_embed=True
        )

    # --------------------------- GENERIC COMMANDS ----------------------------
    @command_audioset.command(name="info", aliases=["settings"])
    @commands.guild_only()
    async def command_audioset_settings(self, ctx: commands.Context):
        """Show the settings for the current context.

        This takes into consideration where the command is ran, if the music is playing on the current server and the user who run it.
        """
        dj_roles = await self.config_cache.dj_roles.get_context_value(
            ctx.guild
        )
        dj_enabled = await self.config_cache.dj_status.get_context_value(
            ctx.guild
        )
        emptydc_enabled = await self.config_cache.empty_dc.get_context_value(
            ctx.guild
        )
        emptydc_timer = (
            await self.config_cache.empty_dc_timer.get_context_value(ctx.guild)
        )
        emptypause_enabled = (
            await self.config_cache.empty_pause.get_context_value(ctx.guild)
        )
        emptypause_timer = (
            await self.config_cache.empty_dc_timer.get_context_value(ctx.guild)
        )
        jukebox = await self.config_cache.jukebox.get_context_value(ctx.guild)
        jukebox_price = (
            await self.config_cache.jukebox_price.get_context_value(ctx.guild)
        )
        thumbnail = await self.config_cache.thumbnail.get_context_value(
            ctx.guild
        )
        dc = await self.config_cache.disconnect.get_context_value(ctx.guild)
        autoplay = await self.config_cache.autoplay.get_context_value(
            ctx.guild
        )
        maxlength = await self.config_cache.max_track_length.get_context_value(
            ctx.guild
        )
        maxqueue = await self.config_cache.max_queue_size.get_context_value(
            ctx.guild
        )
        vote_percent = (
            await self.config_cache.votes_percentage.get_context_value(
                ctx.guild
            )
        )
        current_level = (
            await self.config_cache.local_cache_level.get_context_value(
                ctx.guild
            )
        )
        song_repeat = await self.config_cache.repeat.get_context_value(
            ctx.guild
        )
        song_shuffle = await self.config_cache.shuffle.get_context_value(
            ctx.guild
        )
        bumpped_shuffle = (
            await self.config_cache.shuffle_bumped.get_context_value(ctx.guild)
        )
        song_notify = await self.config_cache.notify.get_context_value(
            ctx.guild
        )
        persist_queue = (
            await self.config_cache.persistent_queue.get_context_value(
                ctx.guild
            )
        )
        auto_deafen = await self.config_cache.auto_deafen.get_context_value(
            ctx.guild
        )
        auto_lyrics = await self.config_cache.auto_lyrics.get_context_value(
            ctx.guild
        )
        volume = await self.config_cache.volume.get_context_value(
            ctx.guild,
            channel=self.rgetattr(ctx, "guild.me.voice.channel", None),
        )
        countrycode = await self.config_cache.country_code.get_context_value(
            ctx.guild, user=ctx.author
        )
        cache_enabled = CacheLevel.set_lavalink().is_subset(current_level)
        vote_enabled = await self.config_cache.votes.get_context_value(
            ctx.guild
        )
        msg = "----" + "Context Settings" + "----        \n"
        msg += "Auto-disconnect:  [{dc}]\n".format(
            dc=ENABLED_TITLE if dc else DISABLED_TITLE
        )
        msg += "Auto-play:        [{autoplay}]\n".format(
            autoplay=ENABLED_TITLE if autoplay else DISABLED_TITLE
        )
        msg += "Auto-Lyrics:      [{autoplay}]\n".format(
            autoplay=ENABLED_TITLE if auto_lyrics else DISABLED_TITLE
        )
        if emptydc_enabled:
            msg += "Disconnect timer: [{num_seconds}]\n".format(
                num_seconds=self.get_time_string(emptydc_timer)
            )
        if emptypause_enabled:
            msg += "Auto Pause timer: [{num_seconds}]\n".format(
                num_seconds=self.get_time_string(emptypause_timer)
            )
        if dj_enabled and dj_roles:
            msg += "DJ Roles:         [{number}]\n".format(
                number=len(dj_roles)
            )
        if jukebox:
            msg += "Jukebox:          [{jukebox_name}]\n".format(
                jukebox_name=jukebox
            )
            msg += "Command price:    [{jukebox_price}]\n".format(
                jukebox_price=humanize_number(jukebox_price)
            )
        if maxlength > 0:
            msg += "Max track length: [{length}]\n".format(
                length=self.get_time_string(maxlength)
            )
        if maxqueue > 0:
            msg += "Max queue length: [{length}]\n".format(
                length=humanize_number(maxqueue)
            )

        msg += (
            "Repeat:           [{repeat}]\n"
            "Shuffle:          [{shuffle}]\n"
            "Shuffle bumped:   [{bumpped_shuffle}]\n"
            "Song notify msgs: [{notify}]\n"
            "Persist queue:    [{persist_queue}]\n"
            "Spotify search:   [{countrycode}]\n"
            "Auto-deafen:      [{auto_deafen}]\n"
            "Volume:           [{volume}%]\n"
        ).format(
            countrycode=countrycode,
            repeat=song_repeat,
            shuffle=song_shuffle,
            notify=song_notify,
            bumpped_shuffle=bumpped_shuffle,
            persist_queue=persist_queue,
            auto_deafen=auto_deafen,
            volume=volume,
        )
        if thumbnail:
            msg += "Thumbnails:       [{0}]\n".format(
                ENABLED_TITLE if thumbnail else DISABLED_TITLE
            )
        if vote_percent > 0:
            msg += (
                "Vote skip:        [{vote_enabled}]\nVote percentage:  [{vote_percent}%]\n"
            ).format(
                vote_percent=vote_percent,
                vote_enabled=ENABLED_TITLE if vote_enabled else DISABLED_TITLE,
            )

        autoplaylist = await self.config.guild(ctx.guild).autoplaylist()
        if autoplay or autoplaylist["enabled"]:
            if autoplaylist["enabled"]:
                pname = autoplaylist["name"]
                pid = autoplaylist["id"]
                pscope = autoplaylist["scope"]
                if pscope == PlaylistScope.GUILD.value:
                    pscope = "Server"
                elif pscope == PlaylistScope.USER.value:
                    pscope = "User"
                else:
                    pscope = "Global"
            elif cache_enabled:
                pname = "Cached"
                pid = "Cached"
                pscope = "Cached"
            else:
                pname = "US Top 100"
                pid = "US Top 100"
                pscope = "US Top 100"
            msg += (
                "\n---"
                + "Auto-play Settings"
                + "---        \n"
                + "Playlist name:    [{pname}]\n"
                + "Playlist ID:      [{pid}]\n"
                + "Playlist scope:   [{pscope}]\n"
            ).format(pname=pname, pid=pid, pscope=pscope)

        await self.send_embed_msg(
            ctx, description=box(msg, lang="ini"), no_embed=True
        )

    # --------------------------- GENERIC COMMANDS ----------------------------

    @command_audioset.command(name="youtubeapi")
    @commands.is_owner()
    async def command_audioset_youtubeapi(self, ctx: commands.Context):
        """Instructions to set the YouTube API key."""
        message = (
            "1. Go to Google Developers Console and log in with your Google account.\n"
            "(https://console.developers.google.com/)\n"
            "2. You should be prompted to create a new project (name does not matter).\n"
            "3. Click on Enable APIs and Services at the top.\n"
            "4. In the list of APIs choose or search for YouTube Data API v3 and "
            "click on it. Choose Enable.\n"
            "5. Click on Credentials on the left navigation bar.\n"
            "6. Click on Create Credential at the top.\n"
            '7. At the top click the link for "API key".\n'
            "8. No application restrictions are needed. Click Create at the bottom.\n"
            "9. You now have a key to add to `{prefix}set api youtube api_key <your_api_key_here>`"
        ).format(prefix=ctx.prefix)
        await ctx.maybe_send_embed(message)

    @command_audioset.command(name="spotifyapi")
    @commands.is_owner()
    async def command_audioset_spotifyapi(self, ctx: commands.Context):
        """Instructions to set the Spotify API tokens."""
        message = (
            "1. Go to Spotify developers and log in with your Spotify account.\n"
            "(https://developer.spotify.com/dashboard/applications)\n"
            '2. Click "Create An App".\n'
            "3. Fill out the form provided with your app name, etc.\n"
            '4. When asked if you\'re developing commercial integration select "No".\n'
            "5. Accept the terms and conditions.\n"
            "6. Copy your client ID and your client secret into:\n"
            "`{prefix}set api spotify client_id <your_client_id_here> "
            "client_secret <your_client_secret_here>`"
        ).format(prefix=ctx.prefix)
        await ctx.maybe_send_embed(message)
