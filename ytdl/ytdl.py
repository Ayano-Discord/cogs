# Future Imports
from __future__ import annotations

# Standard Library Imports
from typing import Optional
import asyncio
import datetime
import functools
import itertools
import json
import logging
import math
import random
import re
import textwrap
import urllib

# Dependency Imports
from async_timeout import timeout
from humanize.time import precisedelta
from redbot.core import commands, Config
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate
import aiohttp
import discord
import humanize
import yt_dlp as youtube_dl

# Music Imports
from .flags import Search
from .tracks import hibiki_titles, titles

log = logging.getLogger("red.cogs.YTDLMusic")


youtube_dl.utils.bug_reports_message = lambda: ""


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        "format": "bestaudio/best",
        "extractaudio": True,
        "audioformat": "mp3",
        "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
    }

    FFMPEG_OPTIONS = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn",
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(
        self,
        ctx: commands.Context,
        source: discord.FFmpegPCMAudio,
        *,
        data: dict,
        volume: float = 0.5,
    ):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get("uploader")
        self.uploader_url = data.get("uploader_url")
        date = data.get("upload_date")
        self.upload_date = date[6:8] + "." + date[4:6] + "." + date[0:4]
        self.title = data.get("title")
        self.thumbnail = data.get("thumbnail")
        self.description = data.get("description")
        self.duration = self.parse_duration(int(data.get("duration")))
        self.tags = data.get("tags")
        self.url = data.get("webpage_url")
        self.views = data.get("view_count")
        self.likes = data.get("like_count")
        self.dislikes = data.get("dislike_count")
        self.stream_url = data.get("url")

    def __str__(self):
        return "**`{0.title}`** by **`{0.uploader}`**".format(self)

    @classmethod
    async def create_source(
        cls,
        ctx: commands.Context,
        search: str,
        *,
        loop: asyncio.BaseEventLoop = None,
    ):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(
            cls.ytdl.extract_info, search, download=False, process=False
        )
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError(
                "Couldn't find anything that matches `{}`".format(search)
            )

        if "entries" not in data:
            process_info = data
        else:
            process_info = None
            for entry in data["entries"]:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError(
                    "Couldn't find anything that matches `{}`".format(search)
                )

        webpage_url = process_info["webpage_url"]
        partial = functools.partial(
            cls.ytdl.extract_info, webpage_url, download=False
        )
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError("Couldn't fetch `{}`".format(webpage_url))

        if "entries" not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info["entries"].pop(0)
                except IndexError:
                    raise YTDLError(
                        "Couldn't retrieve any matches for `{}`".format(
                            webpage_url
                        )
                    )

        return cls(
            ctx,
            discord.FFmpegPCMAudio(info["url"], **cls.FFMPEG_OPTIONS),
            data=info,
        )

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append("{} days".format(days))
        if hours > 0:
            duration.append("{} hours".format(hours))
        if minutes > 0:
            duration.append("{} minutes".format(minutes))
        if seconds > 0:
            duration.append("{} seconds".format(seconds))
        else:
            duration.append("LIVE STREAMING")

        return ", ".join(duration)


class Song:
    __slots__ = ("source", "requester")

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        em = (
            discord.Embed(
                description="```css\n{0.source.title}\n```".format(self),
                color=0xF395A5,
            )
            .add_field(
                name=":timer: Duration",
                value=f"`{self.source.duration}`",
                inline=True,
            )
            .add_field(
                name="<:users:906539025345699842> Requested by",
                value=self.requester.mention,
                inline=True,
            )
            .add_field(
                name=":artist: Artist",
                value="[{0.source.uploader}]({0.source.uploader_url})".format(
                    self
                ),
            )
            .add_field(
                name="<a:eyesshaking:906537127913861150> Total Views",
                value="`{}`".format(humanize.intword(self.source.views)),
            )
            .add_field(
                name="<a:thumbs_up:906536086015209493> Total Likes",
                value="`{}`".format(humanize.intword(self.source.likes)),
            )
            .add_field(
                name="<a:thumbs_down:906536159600074775> Total Dislikes",
                value="`{}`".format(humanize.intword(self.source.dislikes)),
            )
            .set_thumbnail(url=self.source.thumbnail)
            .set_footer(
                text=f"Requested by {self.requester.name} (In streaming)",
                icon_url=f"{self.requester.avatar.url}",
            )
        )

        return em

    def song_name(self):
        return self.source.title


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(
                itertools.islice(self._queue, item.start, item.stop, item.step)
            )
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return

            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            await self.current.source.channel.send(
                embed=self.current.create_embed()
            )

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Music(commands.Cog):

    __slots__ = ("source", "requester")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}
        self.config = Config.get_conf(
            self, identifier=234395307759108106, force_registration=True
        )
        default_guild = {
            "dj_enabled": False,
            "dj_roles": [],
        }
        default_global = {"total_songs_played": 0}
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        self.total_songs_played = self.config.total_songs_played()
        self.session_songs_played = 0
        # self.source = source
        # self.data = json.load(
        #     open("/home/ubuntu/mine/ytdl/data.json", "r")
        # )

    # @commands.Cog.listener()
    # async def on_ready(self):
    #     print(f"Music Loaded")

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())
        log.info(
            "I played a total of {} songs this session.".format(
                self.session_songs_played
            )
        )
        self.session_songs_played = 0

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage(
                "This command can't be used in DM channels."
            )

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        await ctx.send("An error occurred: {}".format(str(error)))

    @commands.command(name="musicstats", aliases=["audiostats"])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def music_stats(self, ctx: commands.Context):
        """
        Shows the amount of songs played.
        """
        async with ctx.typing():
            data = json.load(open("/home/ubuntu/mine/ytdl/data.json", "r"))
            total_played = data["total_songs_played"]
            await ctx.send(
                "I played a total of {} songs this session and I have played {} totally".format(
                    self.session_songs_played, total_played
                )
            )

    @commands.command(
        help="Make me join in a VC",
        name="join",
        invoke_without_subcommand=True,
    )
    async def _join(self, ctx: commands.Context):

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)

        ctx.voice_state.voice = await destination.connect()

        em = discord.Embed(
            title=f":zzz: Joined in {destination}", color=ctx.author.color
        )
        em.set_footer(text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=em)

    @commands.command(help="Summon me in a VC", aliases=["summon"])
    async def _summon(
        self, ctx: commands.Context, *, channel: discord.VoiceChannel = None
    ):

        if not channel and not ctx.author.voice:
            raise VoiceError(
                "You are neither connected to a voice channel / not specified a channel to join."
            )

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            em = discord.Embed(
                title=f":zzz: Summoned in {destination}",
                color=ctx.author.color,
            )
            em.set_footer(text=f"Requested by {ctx.author.name}")
            await ctx.send(embed=em)

        ctx.voice_state.voice = await destination.connect()

    @commands.command(
        help="Make me leave a VC", name="disconnect", aliases=["dc"]
    )
    async def _disconnect(self, ctx: commands.Context):

        if not ctx.voice_state.voice:
            return await ctx.send("Not connected to any voice channel.")

        if ctx.author.voice.channel != ctx.guild.me.voice.channel:
            return await ctx.send("You aren't in my voice channel.")

        dest = ctx.author.voice.channel
        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]
        em = discord.Embed(
            title=f":zzz: Disconnected from {dest}", color=ctx.author.color
        )
        em.set_footer(text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=em)

    # Search whatever u want on youtube!
    @commands.command(help="Search something on YouTube")
    async def syt(self, ctx, *, search):

        query_string = urllib.parse.urlencode({"search_query": search})
        html_content = urllib.request.urlopen(
            "http://youtube.com/results?" + query_string
        )

        search_content = re.findall(
            r"watch\?v=(\S{11})", html_content.read().decode()
        )
        em = discord.Embed(
            title=":bulb: **Search Result**",
            description="http://youtube.com/watch?v=" + search_content[0],
            color=ctx.author.color,
        )
        em.set_thumbnail(
            url="https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/3eec9ebd-3641-4be9-a528-1f313300ff3c/dcq4cdk-935e7508-ea87-4896-a084-6a5aaa680d51.png?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOiIsImlzcyI6InVybjphcHA6Iiwib2JqIjpbW3sicGF0aCI6IlwvZlwvM2VlYzllYmQtMzY0MS00YmU5LWE1MjgtMWYzMTMzMDBmZjNjXC9kY3E0Y2RrLTkzNWU3NTA4LWVhODctNDg5Ni1hMDg0LTZhNWFhYTY4MGQ1MS5wbmcifV1dLCJhdWQiOlsidXJuOnNlcnZpY2U6ZmlsZS5kb3dubG9hZCJdfQ.8JGq4xvhJZOncfRybw4z3Jhk0vE9B3oiD4aA3dOZqv0"
        )
        em.set_footer(
            text=f"Search requested by {ctx.author.name}",
            icon_url=f"{ctx.author.avatar.url}",
        )
        await ctx.send(embed=em)

    @commands.command(
        name="volume", help="Set the player volume", aliases=["vol"]
    )
    async def _volume(self, ctx: commands.Context, *, volume: int):

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send(
                "You are not connected to any voice channel."
            )

        if not ctx.voice_state.is_playing:
            return await ctx.send("Nothing being played at the moment.")

        if ctx.author.voice.channel != ctx.guild.me.voice.channel:
            return await ctx.send("You aren't in my voice channel.")

        if volume > 150:
            return await ctx.send(":x: Volume must be between **0 and 150**")

        ctx.voice_client.source.volume = volume / 150
        em = discord.Embed(
            title=f"Volume set at the **`{volume}%`**", color=ctx.author.color
        )
        em.set_footer(text=f"Regulated by {ctx.author.name}")
        await ctx.send(embed=em)

    @commands.command(
        help="See the actual song in playing",
        aliases=["np", "current", "playing", "now"],
        name="nowplaying",
    )
    async def _now(self, ctx: commands.Context):

        await ctx.send(embed=ctx.voice_state.current.create_embed())

    @commands.command(name="pause", help="Pause the actual player")
    async def _pause(self, ctx):
        server = ctx.message.guild
        voice_channel = server.voice_client

        if ctx.author.voice.channel != ctx.guild.me.voice.channel:
            return await ctx.send("You aren't in my voice channel.")

        voice_channel.pause()
        await ctx.message.add_reaction("⏯")

    @commands.command(name="resume", help="Resume the paused player")
    async def _resume(self, ctx):
        server = ctx.message.guild
        voice_channel = server.voice_client

        if ctx.author.voice.channel != ctx.guild.me.voice.channel:
            return await ctx.send("You aren't in my voice channel.")

        voice_channel.resume()
        await ctx.message.add_reaction("⏯")

    @commands.command(name="stop", help="Stop the current song")
    async def _stop(self, ctx):

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send(
                "You are not connected to any voice channel."
            )

        if ctx.author.voice.channel != ctx.guild.me.voice.channel:
            return await ctx.send("You aren't in my voice channel.")

        em = discord.Embed(
            title=f":zzz: Alright, i'll stop the current song.",
            color=ctx.author.color,
        )
        em.set_footer(
            text=f"Stopped by {ctx.author.name}",
            icon_url=f"{ctx.author.avatar.url}",
        )
        await ctx.send(embed=em)
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        voice.stop()

    @commands.command(name="skip", help="Skip the current song")
    async def _skip(self, ctx: commands.Context):

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send(
                "You are not connected to any voice channel."
            )

        if not ctx.voice_state.is_playing:
            return await ctx.send("Not playing any music right now...")

        if ctx.author.voice.channel != ctx.guild.me.voice.channel:
            return await ctx.send("You aren't in my voice channel.")

        voter = ctx.message.author
        if voter == ctx.voice_state.current.requester:
            await ctx.message.add_reaction("⏭")
            ctx.voice_state.skip()

        elif voter.id != ctx.voice_state.current.requester:
            if (
                ctx.voice_state.current.requester
                not in ctx.author.voice.channel.members
            ):
                await ctx.message.add_reaction("⏭")
                ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)
            needed_dict = []
            for user in ctx.guild.me.voice.channel.members:
                needed_dict.append(user.id)
            needed_dict.pop(needed_dict.index(self.bot.user.id))
            needed_votes = round(len(needed_dict) / 2)

            if total_votes >= needed_votes:
                await ctx.message.add_reaction("⏭")
                skipped_embed = discord.Embed(
                    title="Skipped",
                    description=f"{ctx.voice_state.current.title}",
                    color=await ctx.embed_colour(),
                )
                skipped_embed.set_footer(
                    text=f"Skipped by {ctx.author.name}",
                    icon_url=f"{ctx.author.avatar.url}",
                )
                await ctx.send(embed=skipped_embed)
                ctx.voice_state.skip()
                if len(ctx.voice_state.songs) == 0:
                    return
                now_playing_embed = discord.Embed(
                    title="Now playing",
                    description=f"{ctx.voice_state.current.title}",
                    color=await ctx.embed_colour(),
                )
                await ctx.send(embed=now_playing_embed)

            else:
                await ctx.send(
                    "Skip vote added, currently at **{}/{}**".format(
                        total_votes, needed_votes
                    )
                )

        else:
            await ctx.send("You have already voted to skip this song.")

    @commands.command(name="queue", help="See the song queue")
    async def _queue(self, ctx: commands.Context, *, page: int = 1):

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send("The queue is empty.")

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ""
        for i, song in enumerate(
            ctx.voice_state.songs[start:end], start=start
        ):
            queue += "`{0}.` [**{1.source.title}**]({1.source.url})\n`{1.source.duration}`\n\n".format(
                i + 1, song
            )

        embed = discord.Embed(
            description="**{} Tracks:**\n\n{}".format(
                len(ctx.voice_state.songs), queue
            )
        ).set_footer(text="Viewing page {}/{}".format(page, pages))
        await ctx.send(embed=embed)

    @commands.command(name="shuffle", help="Shuffle the queue")
    async def _shuffle(self, ctx: commands.Context):

        if ctx.author.voice.channel != ctx.guild.me.voice.channel:
            return await ctx.send("You aren't in my voice channel.")

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send("Empty queue.")

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction("✅")

    @commands.command(name="remove", help="Remove a song from the queue")
    async def _remove(self, ctx: commands.Context, index: int):

        if ctx.author.voice.channel != ctx.guild.me.voice.channel:
            return await ctx.send("You aren't in my voice channel.")

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send("Empty queue.")

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction("✅")

    @commands.command(name="play", help="Play a song in a VC")
    async def _play(
        self,
        ctx: commands.Context,
        *,
        search: str,
    ):
        """
        Play a song

        Usage:
            [p]play <song name>

        Arguements:
            search: The song name to search for

            Instead of specifying the song name, you can use the following flags:
                    --random:
                        Play a random song from our list of curated tracks.
                    --hibiki:
                        Play a random song about Hibiki.

                NOTE: IF YOU DECIDE TO SPECIFY BOTH FLAGS, `--hibiki` WILL GAIN PRIORITY OVER `--random`.
        """
        async with ctx.typing():

            if search is None:
                return await ctx.send(
                    "You need to specify a song name or a flag, run `%help play` for more information."
                )

            data = json.load(open("/home/ubuntu/mine/ytdl/data.json", "r"))
            data["total_songs_played"] += 1
            json.dump(data, open("/home/ubuntu/mine/ytdl/data.json", "w"))
            self.session_songs_played += 1
            if not ctx.voice_state.voice:
                await ctx.invoke(self._join)

            if search.lower() == "--hibiki":
                if search.lower() == "random":
                    await ctx.send(
                        "You can't specify both flags, run `%help play` for more information."
                    )

            if search.lower() == "--hibiki":
                song = random.choice(hibiki_titles)
                try:
                    source = await YTDLSource.create_source(
                        ctx, song, loop=self.bot.loop
                    )
                except YTDLError as e:
                    await ctx.send("**`ERROR`**: {}".format(str(e)))
                else:
                    song2 = Song(source)

                await ctx.voice_state.songs.put(song2)
                await ctx.send(":headphones: Enqueued {}".format(str(source)))
                return

            if search.lower() == "--random":
                song = random.choice(titles)
                try:
                    source = await YTDLSource.create_source(
                        ctx, song, loop=self.bot.loop
                    )
                except YTDLError as e:
                    await ctx.send("**`ERROR`**: {}".format(str(e)))
                else:
                    song2 = Song(source)

                await ctx.voice_state.songs.put(song2)
                await ctx.send(":headphones: Enqueued {}".format(str(source)))
                return

            try:
                source = await YTDLSource.create_source(
                    ctx, search, loop=self.bot.loop
                )
            except YTDLError as e:
                await ctx.send("**`ERROR`**: {}".format(str(e)))
            else:
                song = Song(source)

            await ctx.voice_state.songs.put(song)
            await ctx.send(":headphones: Enqueued {}".format(str(source)))

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError(
                "You are not connected to any voice channel."
            )

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError("I'm already in a voice channel.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        try:
            if len(after.channel.members) == 1:
                await self.get_voice_state(self).stop()
                del self.voice_states[after.guild.id]
            bots = []
            for member in after.channel.members:
                if member.bot:
                    bots.append(member.id)
            if len(bots) == len(after.channel.members):
                await self.get_voice_state(self).stop()
                del self.voice_states[after.guild.id]
        except AttributeError:
            pass

    # @commands.command(name="spotify", aliases=["sp"])
    # async def _spotify(
    #     self, ctx: commands.Context, *, user: discord.Member = None
    # ):
    #     """
    #     See what a user is listening to on spotify

    #     and have an option of adding it to the queue
    #     """
    #     if user is None:
    #         user = ctx.author

    #     if user.activities:
    #         for activity in user.activities:
    #             if isinstance(activity, discord.Spotify):
    #                 embed = discord.Embed(
    #                     titl=f"{user.name}'s Spotify",
    #                     description="{} Listening to {}".format(
    #                         user.mention, activity.title
    #                     ),
    #                     color=await ctx.embed_color(),
    #                 )
    #                 embed.set_thumbnail(url=activity.album_cover_url)
    #                 embed.add_field(name="Artist", value=activity.artist)
    #                 embed.add_field(name="Album", value=activity.album)
    #                 embed.set_footer(
    #                     text="Song started at {}".format(
    #                         activity.created_at.strftime("%H:%M")
    #                     )
    #                 )
    #                 await ctx.send(embed=embed)
    #                 msg = await ctx.send(
    #                     "Would you like to add this song to the queue?"
    #                 )
    #                 start_adding_reactions(
    #                     msg, ReactionPredicate.YES_OR_NO_EMOJIS
    #                 )

    #                 pred = ReactionPredicate.yes_or_no(msg, ctx.author)
    #                 await ctx.bot.wait_for("reaction_add", check=pred)
    #                 if pred.result is True:
    #                     await ctx.invoke(self._play, search=activity.title)
    #                     await ctx.send("Song added to queue")
    #                     return
    #                 else:
    #                     await ctx.send("Ok, I won't add the song to the queue")
    #                     msg.clear_reactions()
    #                     return
    #             # else:
    #             #     return await ctx.send(
    #             #         "{} is not listening to Spotify.".format(user.name)
    #             #     )
    #     else:
    #         return await ctx.send(
    #             "{} is not listening to Spotify.".format(user.name)
    #         )

    @commands.command(
        aliases=["l", "lyrc", "lyric"],
        name="lyrics",
    )  # adding aliases to the command so they they can be triggered with other names
    async def _lyrics(self, ctx, *, search=None):
        """A command to find lyrics easily!"""
        # source = YTDLSource
        async with ctx.typing():
            if (
                not search
            ):  # if user hasnt given an argument, throw a error and come out of the command
                # player = ctx.voice_state.current
                song = urllib.parse.quote(ctx.voice_state.current.song_name())
            else:
                song = urllib.parse.quote(
                    search
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

            # sometimes the song's lyrics can be above 4096 characters, and if it is then we will not be able to send it in one single message on Discord due to the character limit
            # this is why we split the song into chunks of 4096 characters and send each part individually
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
                await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True, name="dj")
    @commands.guild_only()
    async def _dj(self, ctx: commands.Context):
        """
        DJ settings, such as toggling and setting the role.
        """
        dj_enabled = self.config.guild(ctx.guild).dj_enabled()

        if dj_enabled is True:
            await self.config.guild(ctx.guild).dj_enabled.set(False)
            await ctx.send("DJ mode has been disabled.")
        else:
            await self.config.guild(ctx.guild).dj_enabled.set(True)
            await ctx.send("DJ mode has been enabled.")

    @_dj.command(name="add")
    @commands.guild_only()
    async def dj_add(self, ctx: commands.Context, *, role: discord.Role):
        """
        Add a DJ role.
        """
        # dj_role = self.config.guild(ctx.guild).dj_roles()

        # if dj_role is not None:
        #     await ctx.send("There is already a DJ role set.")
        #     return

        # my_list = list(dj_role)
        # my_list.append(role.id)
        dj_roles = self.config.guild(ctx.guild)
        async with dj_roles.dj_roles() as roles:
            roles.append(role.id)
        # await self.config.guild(ctx.guild).dj_roles.set(my_list)
        await ctx.send("DJ role added.")

    @_dj.command(name="remove")
    @commands.guild_only()
    async def dj_remove(self, ctx: commands.Context, *, role: discord.Role):
        """
        Remove a DJ role.
        """
        # dj_role = self.config.guild(ctx.guild).dj_roles()

        # if dj_role is not None:
        #     await ctx.send("There is already a DJ role set.")
        #     return

        # my_list = list(dj_role)
        # my_list.append(role.id)
        dj_roles = self.config.guild(ctx.guild)
        async with dj_roles.dj_roles() as roles:
            try:
                roles.pop(roles.index(role.id))
            except ValueError:
                return await ctx.send("That role is not a DJ role.")
        # await self.config.guild(ctx.guild).dj_roles.set(my_list)
        await ctx.send("DJ role Removed.")

    @_dj.command(name="list")
    @commands.guild_only()
    async def dj_list(self, ctx: commands.Context):
        """
        Add a DJ role.
        """
        # dj_role = self.config.guild(ctx.guild).dj_roles()

        # if dj_role is not None:
        #     await ctx.send("There is already a DJ role set.")
        #     return

        # my_list = list(dj_role)
        # my_list.append(role.id)
        dj_roles = self.config.guild(ctx.guild)
        role_list = []
        async with dj_roles.dj_roles() as roles:
            for role in roles:
                #                role_list.append(role)
                _role = discord.utils.get(ctx.guild.roles, id=role)
                embed = discord.Embed(
                    title="DJ Roles", description="".join(_role.name)
                )
        # for role in role_list:
        #     role_mention = discord.utils.get(ctx.guild.roles, id=role)
        await ctx.send(embed=embed)

    # @commands.command(name="tplay")
    # @command.owner_only()
    # async def _tplay(self, ctx: commands.Context, *, url: str):
    #     """
    #     Plays a song from a given url.
    #     """
    #     player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
    #     ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
    #     await ctx.send('Now playing: {}'.format(player.title))


def setup(bot):
    bot.add_cog(Music(bot))
