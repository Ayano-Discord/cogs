# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
from typing import Optional
import datetime
import logging
import re
import textwrap
import urllib

# Dependency Imports
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
import aiohttp
import discord

# My Modded Imports
import lavalink

# Music Imports
from ...utils import BOT_SONG_RE
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Music.cog.Commands.lyrics")


class LyricsCommands(MixinMeta, ABC, metaclass=CompositeMetaClass):
    @commands.group(name="mlyrics")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def command_mlyrics(self, ctx: commands.Context):
        """Get for a songs lyrics."""

    @command_mlyrics.command(name="search")
    async def command_mlyrics_search(self, ctx, *, artistsong: str):
        """
        Returns Lyrics for Song Lookup.
        User arguments - artist/song
        """
        async with ctx.typing():
            title, artist, lyrics, source = await self.get_lyrics_string(
                artistsong
            )
            title = "" if title == "" else f"{title} by {artist}"
            paged_embeds = []
            paged_content = [p for p in pagify(lyrics, page_length=900)]
            for index, page in enumerate(paged_content, start=1):
                embed = discord.Embed(
                    title=f"{title}",
                    description=page,
                    colour=await self.bot.get_embed_color(ctx.channel),
                )
                if source:
                    embed.set_footer(
                        text=f"Requested by {ctx.message.author} | Source: {source} | Page: {index}/{len(paged_content)}"
                    )
                paged_embeds.append(embed)
        await menu(ctx, paged_embeds, controls=DEFAULT_CONTROLS, timeout=180.0)

    @command_mlyrics.command(name="spotify")
    async def command_mlyrics_spotify(
        self, ctx, user: Optional[discord.Member] = None
    ):
        """
        Returns Lyrics from Discord Member song.
        Optional User arguments - Mention/ID, no argument returns your own
        """
        if user is None:
            user = ctx.author
        spot = next(
            (
                activity
                for activity in user.activities
                if isinstance(activity, discord.Spotify)
            ),
            None,
        )
        if spot is None:
            return await self.send_embed_msg(
                ctx,
                title=f"I'm unable to tell what {user.name} is listening to",
            )
        embed = discord.Embed(
            title=f"{user.name}'s Spotify",
            colour=await self.bot.get_embed_color(ctx.channel),
        )
        embed.add_field(name="Song", value=spot.title)
        embed.add_field(name="Artist", value=spot.artist)
        embed.add_field(name="Album", value=spot.album)
        embed.add_field(
            name="Track Link",
            value=f"[{spot.title}](https://open.spotify.com/track/{spot.track_id})",
        )
        embed.set_thumbnail(url=spot.album_cover_url)
        await self.send_embed_msg(ctx, embed=embed)

        async with ctx.typing():
            title, artist, lyrics, source = await self.get_lyrics_string(
                f"{spot.artist} {spot.title}"
            )
            title = "" if title == "" else f"{title} by {artist}"
            paged_embeds = []
            paged_content = [p for p in pagify(lyrics, page_length=900)]
            for index, page in enumerate(paged_content, start=1):
                embed = discord.Embed(
                    title=f"{title}",
                    description=page,
                    colour=await self.bot.get_embed_color(ctx.channel),
                )
                if source:
                    embed.set_footer(
                        text=f"Requested by {ctx.message.author} | Source: {source} | Page: {index}/{len(paged_content)}"
                    )
                paged_embeds.append(embed)
        await menu(ctx, paged_embeds, controls=DEFAULT_CONTROLS, timeout=180.0)

    @command_mlyrics.command(name="playing")
    async def command_mlyrics_playing(self, ctx):
        """
        Returns Lyrics for bot's current track.
        """
        cached = (
            await self.config_cache.currently_playing_name.get_context_value(
                ctx.guild
            )
        )
        if not cached:
            return await self.send_embed_msg(ctx, title="Nothing playing.")
        botsong = BOT_SONG_RE.sub("", cached).strip()
        async with ctx.typing():
            title, artist, lyrics, source = await self.get_lyrics_string(
                botsong
            )
            title = "" if title == "" else f"{title} by {artist}"
            paged_embeds = []
            paged_content = [p for p in pagify(lyrics, page_length=900)]
            for index, page in enumerate(paged_content, start=1):
                embed = discord.Embed(
                    title="{}".format(title),
                    description=page,
                    colour=await self.bot.get_embed_color(ctx.channel),
                )
                if source:
                    embed.set_footer(
                        text=f"Requested by {ctx.message.author} | Source: {source} | Page: {index}/{len(paged_content)}"
                    )
                paged_embeds.append(embed)
        await menu(ctx, paged_embeds, controls=DEFAULT_CONTROLS, timeout=180.0)

    @commands.command(
        aliases=["lyrc", "lyric"]
    )  # adding aliases to the command so they they can be triggered with other names
    async def lyrics(self, ctx, *, search=None):
        """A command to find lyrics easily!"""
        async with ctx.typing():
            # Credits to alec for the search check!
            selfregex = re.compile(
                (
                    r"((\[)|(\()).*(of?ficial|feat\.?|"
                    r"ft\.?|audio|video|lyrics?|remix|HD).*(?(2)]|\))"
                ),
                flags=re.I,
            )
            if (
                not search
            ):  # if user hasnt given an argument, throw a error and come out of the command
                if ctx.author.voice and ctx.guild.me.voice:
                    if ctx.author.voice.channel == ctx.guild.me.voice.channel:
                        try:
                            player = lavalink.get_player(ctx.guild.id)
                        except KeyError:  # no player for that guild
                            player = None
                        title = player.current.title
                        regex_title = selfregex.sub("", title).strip()
                        renamed_title = regex_title.replace("-", "")
                        song = urllib.parse.quote(renamed_title)
                        if not song:
                            await ctx.send("Idk")
            else:
                song = urllib.parse.quote(
                    str(search)
                )  # url-encode the song provided so it can be passed on to the API

            async with aiohttp.ClientSession() as lyricsSession:
                async with lyricsSession.get(
                    f"https://some-random-api.ml/lyrics?title={song}"
                ) as jsondata:  # define jsondata and fetch from API
                    if (
                        not 300 > jsondata.status >= 200
                    ):  # if an unexpected HTTP status code is recieved from the website, throw an error and come out of the command
                        return await ctx.send(
                            f"Recieved poor status code of {jsondata.status}"
                        )

                    lyricsData = (
                        await jsondata.json()
                    )  # load the json data into its json form

            error = lyricsData.get("error")
            if (
                error
            ):  # checking if there is an error recieved by the API, and if there is then throwing an error message and returning out of the command
                return await ctx.send(f"Recieved unexpected error: {error}")

            songLyrics = lyricsData["lyrics"]  # the lyrics
            songArtist = lyricsData["author"]  # the author's name
            songTitle = lyricsData["title"]  # the song's title
            songThumbnail = lyricsData["thumbnail"][
                "genius"
            ]  # the song's picture/thumbnail

            async def create_menu(self, ctx, results):
                embeds = []
                embed_content = [
                    p for p in pagify(results[0], page_length=750)
                ]
                for index, page in enumerate(embed_content):
                    for chunk in textwrap.wrap(
                        songLyrics, 4096, replace_whitespace=False
                    ):
                        embed = discord.Embed(
                            title=songTitle,
                            description=chunk,
                            color=discord.Color.blurple(),
                            timestamp=datetime.datetime.utcnow(),
                        )
                    embed.set_thumbnail(url=songThumbnail)
                    embed.set_thumbnail(url=results[3])
                    if len(embed_content) != 1:
                        embed.set_footer(
                            text=f"Powered by Some Random Api  | Page {index + 1}/{len(embed_content)}"
                        )
                    else:
                        embed.set_footer(text="Powered by Some Random Api ")
                    embeds.append(embed)
                if len(embed_content) != 1:
                    await self.menu(
                        ctx, embeds, controls=DEFAULT_CONTROLS, timeout=120
                    )
                else:
                    await ctx.send(embed=embeds[0])

            await self.create_menu(
                ctx,
            )
