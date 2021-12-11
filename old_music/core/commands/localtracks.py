# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
from pathlib import Path
from typing import MutableMapping
import contextlib
import logging
import math

# Dependency Imports
from redbot.core import commands
from redbot.core.utils.menus import (
    close_menu,
    DEFAULT_CONTROLS,
    menu,
    next_page,
    prev_page,
)
import discord

# Music Imports
from ...audio_dataclasses import LocalPath, Query
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Music.cog.Commands.local_track")


class LocalTrackCommands(MixinMeta, ABC, metaclass=CompositeMetaClass):
    @commands.group(name="local")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def command_local(self, ctx: commands.Context):
        """Local playback commands."""

    @command_local.command(name="folder", aliases=["start"])
    async def command_local_folder(
        self, ctx: commands.Context, *, folder: str = None
    ):
        """Play all songs in a localtracks folder.

        **Usage**:
        ​ ​ ​ ​ `[p]local folder`
        ​ ​ ​ ​ ​ ​ ​ ​ Open a menu to pick a folder to queue.

        ​ ​ `[p]local folder folder_name`
        ​ ​ ​ ​ ​ ​ ​ ​ Queues all of the tracks inside the folder_name folder.
        """
        if not await self.localtracks_folder_exists(ctx):
            return

        if not folder:
            await ctx.invoke(self.command_local_play)
        else:
            folder = folder.strip()
            _dir = LocalPath.joinpath(self.local_folder_current_path, folder)
            if not _dir.exists():
                return await self.send_embed_msg(
                    ctx,
                    title="Folder Not Found",
                    description="Localtracks folder named {name} does not exist.".format(
                        name=folder
                    ),
                )
            query = Query.process_input(
                _dir, self.local_folder_current_path, search_subfolders=True
            )
            await self._local_play_all(ctx, query, from_search=bool(folder))

    @command_local.command(name="play")
    async def command_local_play(self, ctx: commands.Context):
        """Play a local track.

        To play a local track, either use the menu to choose a track or enter in the track path directly with the play command.
        To play an entire folder, use `[p]help local folder` for instructions.

        **Usage**:
        ​ ​ ​ ​ `[p]local play`
        ​ ​ ​ ​ ​ ​ ​ ​ Open a menu to pick a track.

        ​ ​ ​ ​ `[p]play localtracks\\album_folder\\song_name.mp3`
        ​ ​ ​ ​ `[p]play album_folder\\song_name.mp3`
        ​ ​ ​ ​ ​ ​ ​ ​ Use a direct link relative to the localtracks folder.
        """
        if not await self.localtracks_folder_exists(ctx):
            return
        localtracks_folders = await self.get_localtracks_folders(
            ctx, search_subfolders=True
        )
        if not localtracks_folders:
            return await self.send_embed_msg(
                ctx, title="No album folders found."
            )
        async with ctx.typing():
            len_folder_pages = math.ceil(len(localtracks_folders) / 5)
            folder_page_list = []
            for page_num in range(1, len_folder_pages + 1):
                embed = await self._build_search_page(
                    ctx, localtracks_folders, page_num
                )
                folder_page_list.append(embed)

        async def _local_folder_menu(
            context: commands.Context,
            pages: list,
            controls: MutableMapping,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            if message:
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()
                await self._search_button_action(
                    context, localtracks_folders, emoji, page
                )
                return None

        # noinspection PyDictDuplicateKeys
        local_folder_controls = {
            "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}": _local_folder_menu,
            "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}": _local_folder_menu,
            "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}": _local_folder_menu,
            "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}": _local_folder_menu,
            "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}": _local_folder_menu,
            "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}": prev_page,
            "\N{CROSS MARK}": close_menu,
            "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}": next_page,
        }

        dj_enabled = await self.config_cache.dj_status.get_context_value(
            ctx.guild
        )
        if dj_enabled and not await self._can_instaskip(ctx, ctx.author):
            return await menu(ctx, folder_page_list, DEFAULT_CONTROLS)
        else:
            await menu(ctx, folder_page_list, local_folder_controls)

    @command_local.command(name="search")
    async def command_local_search(
        self, ctx: commands.Context, *, search_words
    ):
        """Search for songs across all localtracks folders."""
        if not await self.localtracks_folder_exists(ctx):
            return
        all_tracks = await self.get_localtrack_folder_list(
            ctx,
            (
                Query.process_input(
                    Path(
                        await self.config_cache.localpath.get_context_value(
                            ctx.guild
                        )
                    ).absolute(),
                    self.local_folder_current_path,
                    search_subfolders=True,
                )
            ),
        )
        if not all_tracks:
            return await self.send_embed_msg(
                ctx, title="No album folders found."
            )
        async with ctx.typing():
            search_list = await self._build_local_search_list(
                all_tracks, search_words
            )
        if not search_list:
            return await self.send_embed_msg(ctx, title="No matches.")
        return await ctx.invoke(self.command_search, query=search_list)
