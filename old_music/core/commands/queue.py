# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
from typing import MutableMapping, Optional
import asyncio
import contextlib
import heapq
import logging
import math

# Dependency Imports
from redbot.core import commands
from redbot.core.utils import AsyncIter
from redbot.core.utils.menus import (
    close_menu,
    DEFAULT_CONTROLS,
    menu,
    next_page,
    prev_page,
    start_adding_reactions,
)
from redbot.core.utils.predicates import ReactionPredicate
import discord

# My Modded Imports
import lavalink

# Music Imports
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Music.cog.Commands.queue")


class QueueCommands(MixinMeta, ABC, metaclass=CompositeMetaClass):
    @commands.group(name="queue", invoke_without_command=True)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def command_queue(self, ctx: commands.Context, *, page: int = 1):
        """List the songs in the queue."""

        async def _queue_menu(
            queue_ctx: commands.Context,
            pages: list,
            controls: MutableMapping,
            queue_message: discord.Message,
            queue_page: int,
            timeout: float,
            queue_emoji: str,
        ):
            if queue_message:
                await queue_ctx.send_help(self.command_queue)
                with contextlib.suppress(discord.HTTPException):
                    await queue_message.delete()
                return None

        queue_controls = {
            "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}": prev_page,
            "\N{CROSS MARK}": close_menu,
            "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}": next_page,
            "\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16}": _queue_menu,
        }

        if not self._player_check(ctx):
            return await self.send_embed_msg(
                ctx, title="There's nothing in the queue."
            )
        player = lavalink.get_player(ctx.guild.id)

        if player.current and not player.queue:
            arrow = await self.draw_time(ctx)
            pos = self.format_time(player.position)
            if player.current.is_stream:
                dur = "LIVE"
            else:
                dur = self.format_time(player.current.length)
            song = (
                await self.get_track_description(
                    player.current, self.local_folder_current_path
                )
                or ""
            )
            song += "\n Requested by: **{track.requester.mention}**".format(
                track=player.current
            )
            song += f"\n\n{arrow}`{pos}`/`{dur}`"
            embed = discord.Embed(title="Now Playing", description=song)
            thumbnail = await self.config_cache.thumbnail.get_context_value(
                ctx.guild
            )
            if thumbnail and player.current and player.current.thumbnail:
                embed.set_thumbnail(url=player.current.thumbnail)

            shuffle = await self.config_cache.shuffle.get_context_value(
                ctx.guild
            )
            repeat = await self.config_cache.repeat.get_context_value(
                ctx.guild
            )
            autoplay = await self.config_cache.autoplay.get_context_value(
                ctx.guild
            )
            text = ""
            text += (
                "Auto-Play"
                + ": "
                + (
                    "\N{WHITE HEAVY CHECK MARK}"
                    if autoplay
                    else "\N{CROSS MARK}"
                )
            )
            text += (
                (" | " if text else "")
                + "Shuffle"
                + ": "
                + (
                    "\N{WHITE HEAVY CHECK MARK}"
                    if shuffle
                    else "\N{CROSS MARK}"
                )
            )
            text += (
                (" | " if text else "")
                + "Repeat"
                + ": "
                + (
                    "\N{WHITE HEAVY CHECK MARK}"
                    if repeat
                    else "\N{CROSS MARK}"
                )
            )
            embed.set_footer(text=text)
            message = await self.send_embed_msg(ctx, embed=embed)
            dj_enabled = await self.config_cache.dj_status.get_context_value(
                ctx.guild
            )
            vote_enabled = await self.config_cache.votes.get_context_value(
                ctx.guild
            )
            if (
                (dj_enabled or vote_enabled)
                and not await self._can_instaskip(ctx, ctx.author)
                and not await self.is_requester_alone(ctx)
            ):
                return

            emoji = {
                "prev": "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
                "stop": "\N{BLACK SQUARE FOR STOP}\N{VARIATION SELECTOR-16}",
                "pause": "\N{BLACK RIGHT-POINTING TRIANGLE WITH DOUBLE VERTICAL BAR}\N{VARIATION SELECTOR-16}",
                "next": "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
                "close": "\N{CROSS MARK}",
            }
            expected = tuple(emoji.values())
            if not player.queue and not autoplay:
                expected = (emoji["stop"], emoji["pause"], emoji["close"])
            if player.current:
                task: Optional[asyncio.Task] = start_adding_reactions(
                    message, expected[:5]
                )
            else:
                task: Optional[asyncio.Task] = None

            try:
                (r, u) = await self.bot.wait_for(
                    "reaction_add",
                    check=ReactionPredicate.with_emojis(
                        expected, message, ctx.author
                    ),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                return await self._clear_react(message, emoji)
            else:
                if task is not None:
                    task.cancel()
            reacts = {v: k for k, v in emoji.items()}
            react = reacts[r.emoji]
            if react == "prev":
                await self._clear_react(message, emoji)
                await ctx.invoke(self.command_prev)
            elif react == "stop":
                await self._clear_react(message, emoji)
                await ctx.invoke(self.command_stop)
            elif react == "pause":
                await self._clear_react(message, emoji)
                await ctx.invoke(self.command_pause)
            elif react == "next":
                await self._clear_react(message, emoji)
                await ctx.invoke(self.command_skip)
            elif react == "close":
                await message.delete()
            return
        elif not player.current and not player.queue:
            return await self.send_embed_msg(
                ctx, title="There's nothing in the queue."
            )

        async with ctx.typing():
            limited_queue = player.queue[
                :500
            ]  # TODO: Improve when Toby menu's are merged
            len_queue_pages = math.ceil(len(limited_queue) / 15)
            queue_page_list = []
            async for page_num in AsyncIter(range(1, len_queue_pages + 1)):
                embed = await self._build_queue_page(
                    ctx, limited_queue, player, page_num
                )
                queue_page_list.append(embed)
            if page > len_queue_pages:
                page = len_queue_pages
        return await menu(
            ctx, queue_page_list, queue_controls, page=(page - 1)
        )

    @command_queue.command(name="clear", aliases=["wipe", "reset"])
    async def command_queue_clear(self, ctx: commands.Context):
        """Clears the queue."""
        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self.send_embed_msg(
                ctx, title="There's nothing in the queue."
            )
        dj_enabled = await self.config_cache.dj_status.get_context_value(
            ctx.guild
        )
        if not self._player_check(ctx) or not player.queue:
            return await self.send_embed_msg(
                ctx, title="There's nothing in the queue."
            )
        if (
            dj_enabled
            and not await self._can_instaskip(ctx, ctx.author)
            and not await self.is_requester_alone(ctx)
        ):
            return await self.send_embed_msg(
                ctx,
                title="Unable To Clear Queue",
                description="You need the DJ role to clear the queue.",
            )
        async for track in AsyncIter(player.queue):
            await self.api_interface.persistent_queue_api.played(
                ctx.guild.id, track.extras.get("enqueue_time")
            )
        player.queue.clear()
        await self.send_embed_msg(
            ctx,
            title="Queue Modified",
            description="The queue has been cleared.",
        )

    @command_queue.command(name="clean")
    async def command_queue_clean(self, ctx: commands.Context):
        """Removes songs from the queue if the requester is not in the voice channel."""
        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self.send_embed_msg(
                ctx, title="There's nothing in the queue."
            )
        dj_enabled = await self.config_cache.dj_status.get_context_value(
            ctx.guild
        )
        if not self._player_check(ctx) or not player.queue:
            return await self.send_embed_msg(
                ctx, title="There's nothing in the queue."
            )
        if (
            dj_enabled
            and not await self._can_instaskip(ctx, ctx.author)
            and not await self.is_requester_alone(ctx)
        ):
            return await self.send_embed_msg(
                ctx,
                title="Unable To Clean Queue",
                description="You need the DJ role to clean the queue.",
            )
        clean_tracks = []
        removed_tracks = 0
        listeners = player.channel.members
        async for track in AsyncIter(player.queue.copy()):
            if track.requester in listeners:
                clean_tracks.append(track)
            else:
                await self.api_interface.persistent_queue_api.played(
                    ctx.guild.id, track.extras.get("enqueue_time")
                )
                removed_tracks += 1
        player.queue = clean_tracks
        if removed_tracks == 0:
            await self.send_embed_msg(ctx, title="Removed 0 tracks.")
        else:
            await self.send_embed_msg(
                ctx,
                title="Removed Tracks From The Queue",
                description=(
                    "Removed {removed_tracks} tracks queued by members "
                    "outside of the voice channel."
                ).format(removed_tracks=removed_tracks),
            )

    @command_queue.command(name="cleanself")
    async def command_queue_cleanself(self, ctx: commands.Context):
        """Removes all tracks you requested from the queue."""

        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self.send_embed_msg(
                ctx, title="There's nothing in the queue."
            )
        if not self._player_check(ctx) or not player.queue:
            return await self.send_embed_msg(
                ctx, title="There's nothing in the queue."
            )

        clean_tracks = []
        removed_tracks = 0
        async for track in AsyncIter(player.queue.copy()):
            if track.requester != ctx.author:
                clean_tracks.append(track)
            else:
                removed_tracks += 1
                await self.api_interface.persistent_queue_api.played(
                    ctx.guild.id, track.extras.get("enqueue_time")
                )
        player.queue = clean_tracks
        if removed_tracks == 0:
            await self.send_embed_msg(ctx, title="Removed 0 tracks.")
        else:
            await self.send_embed_msg(
                ctx,
                title="Removed Tracks From The Queue",
                description=(
                    "Removed {removed_tracks} tracks queued by {member.display_name}."
                ).format(removed_tracks=removed_tracks, member=ctx.author),
            )

    @command_queue.command(name="search")
    async def command_queue_search(
        self, ctx: commands.Context, *, search_words: str
    ):
        """Search the queue."""
        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self.send_embed_msg(
                ctx, title="There's nothing in the queue."
            )
        if not self._player_check(ctx) or not player.queue:
            return await self.send_embed_msg(
                ctx, title="There's nothing in the queue."
            )

        search_list = await self._build_queue_search_list(
            player.queue.copy(), search_words
        )
        if not search_list:
            return await self.send_embed_msg(ctx, title="No matches.")

        len_search_pages = math.ceil(len(search_list) / 15)
        search_page_list = []
        async for page_num in AsyncIter(range(1, len_search_pages + 1)):
            embed = await self._build_queue_search_page(
                ctx, page_num, search_list
            )
            search_page_list.append(embed)
        await menu(ctx, search_page_list, DEFAULT_CONTROLS)

    @command_queue.command(name="shuffle")
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def command_queue_shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""
        dj_enabled = await self.config_cache.dj_status.get_context_value(
            ctx.guild
        )
        if (
            dj_enabled
            and not await self._can_instaskip(ctx, ctx.author)
            and not await self.is_requester_alone(ctx)
        ):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title="Unable To Shuffle Queue",
                description="You need the DJ role to shuffle the queue.",
            )
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title="Unable To Shuffle Queue",
                description="There's nothing in the queue.",
            )
        try:
            vc = (
                ctx.guild.me.voice.channel
                if ctx.guild.me.voice
                else ctx.author.voice.channel
            )
            if not self.can_join_and_speak(vc) or self.is_vc_full(vc):
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title="Unable To Shuffle Queue",
                    description="I don't have permission to connect and speak in your channel.",
                )
            player = await lavalink.connect(
                vc,
                deafen=await self.config_cache.auto_deafen.get_context_value(
                    ctx.guild
                ),
            )
            player.store("notify_channel", ctx.channel.id)
        except AttributeError:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title="Unable To Shuffle Queue",
                description="Connect to a voice channel first.",
            )
        except IndexError:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title="Unable To Shuffle Queue",
                description="Connection to Lavalink has not yet been established.",
            )
        except KeyError:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title="Unable To Shuffle Queue",
                description="There's nothing in the queue.",
            )

        if not self._player_check(ctx) or not player.queue:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title="Unable To Shuffle Queue",
                description="There's nothing in the queue.",
            )

        player.force_shuffle(0)
        return await self.send_embed_msg(ctx, title="Queue has been shuffled.")

    @command_queue.command(
        name="ratio", aliases=["%", "percentage", "percent"]
    )
    async def command_queue_percent(self, ctx: commands.Context):
        """Queue percentage."""
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        player = lavalink.get_player(ctx.guild.id)
        queue_tracks = player.queue
        requesters = {"total": 0, "users": {}}

        async def _usercount(req_username):
            if req_username in requesters["users"]:
                requesters["users"][req_username]["songcount"] += 1
            else:
                requesters["users"][req_username] = {"songcount": 1}

            requesters["total"] += 1

        async for track in AsyncIter(queue_tracks):
            req_username = (
                track.requester.mention if track.requester else ctx.me.mention
            )
            await _usercount(req_username)

        try:
            req_username = (
                player.current.requester.mention
                if player.current and player.current.requester
                else ctx.me.mention
            )
            await _usercount(req_username)
        except AttributeError:
            return await self.send_embed_msg(
                ctx, title="There's nothing in the queue."
            )

        async for req_username in AsyncIter(requesters["users"]):
            percentage = float(
                requesters["users"][req_username]["songcount"]
            ) / float(requesters["total"])
            requesters["users"][req_username]["percent"] = round(
                percentage * 100, 1
            )

        top_queue_users = heapq.nlargest(
            20,
            [
                (x, requesters["users"][x][y])
                for x in requesters["users"]
                for y in requesters["users"][x]
                if y == "percent"
            ],
            key=lambda x: x[1],
        )
        queue_user = [f"{x[0]}: {x[1]:g}%" for x in top_queue_users]
        queue_user_list = "\n".join(queue_user)
        await self.send_embed_msg(
            ctx,
            title="Queued and playing tracks:",
            description=queue_user_list,
        )
