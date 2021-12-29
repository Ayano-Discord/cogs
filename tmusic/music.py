# Future Imports
from __future__ import annotations

# Standard Library Imports
import asyncio
import datetime
import re
import typing as t

# Dependency Imports
from discord.ext import menus
from redbot.core import commands
import discord
import humanize
import ujson
import wavelink

URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"


class AlreadyConnectedToChannel(commands.CommandError):
    pass


class NoVoiceChannel(commands.CommandError):
    pass


class QueueIsEmpty(commands.CommandError):
    pass


class NoTracksFound(commands.CommandError):
    pass


class PlayerIsAlreadyPaused(commands.CommandError):
    pass


class NoMoreTracks(commands.CommandError):
    pass


class NoPreviousTracks(commands.CommandError):
    pass


class InvalidRepeatMode(commands.CommandError):
    pass


class VolumeTooLow(commands.CommandError):
    pass


class VolumeTooHigh(commands.CommandError):
    pass


class MaxVolume(commands.CommandError):
    pass


class MinVolume(commands.CommandError):
    pass


class NoLyricsFound(commands.CommandError):
    pass


class InvalidEQPreset(commands.CommandError):
    pass


class NonExistentEQBand(commands.CommandError):
    pass


class EQGainOutOfBounds(commands.CommandError):
    pass


class InvalidTimeString(commands.CommandError):
    pass


class NoNodesAvaiable(Exception):
    pass


class QueueMenuSource(menus.ListPageSource):
    def __init__(self, data):
        super().__init__(data, per_page=10)

    async def format_page(self, menu, entries):

        return {
            "embed": discord.Embed(
                color=menu.ctx.bot.color,
                title=f"Music queue",
                description="\n".join(
                    f"[**{i.title}**]({i.uri})\n{i.author or 'no author'}"
                    for i in entries
                ),
            )
        }


class Track(wavelink.Track):
    __slots__ = ("requester",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        self.requester = kwargs.get("requester")


class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.now_playing = None
        self.deafen = False
        self.no_leave = False
        self.query = None
        self.started = False
        self.is_waiting = True
        self.repeat = False
        self.ctx = None
        self.loop = False
        self.queue = []
        self.queue_position = 0

    async def make_embed(self, ctx, track):

        embed = discord.Embed(
            color=await ctx.embed_color(),
            title="Now playing",
            description=f"Now playing: **{track.title}**\nVolume: {self.volume}",
        )
        try:
            hours, remainder = divmod(track.length / 1000, 3600)
            minutes, seconds = divmod(remainder, 60)

            duration = "%02d:%02d:%02d" % (hours, minutes, seconds)
        except:
            duration = "Duration too long"
        try:
            hours, remainder = divmod(self.position / 1000, 3600)
            minutes, seconds = divmod(remainder, 60)
            position = "%02d:%02d:%02d" % (hours, minutes, seconds)
        except:
            position = "Position too long"
        try:
            percentage = 100 / track.length * self.position
            bar = (
                "`"
                + "⬜" * int(20 / 100 * percentage)
                + "⬛" * int(20 - (20 / 100 * percentage))
                + "`"
            )
        except:
            bar = ""
        embed.description += (
            f"\nCurrent Position: {position} / {duration}"
            if not track.is_stream
            else "Live Stream"
        )
        embed.description += (
            f"\n{bar}" if not track.is_stream else "Live Stream"
        )
        embed.set_thumbnail(url=track.thumb) if track.thumb else ...
        embed.add_field(name="Requester", value=track.requester)
        if track.is_stream:
            embed.add_field(name="Duration", value="Live Stream")
        else:
            embed.add_field(name="Duration", value=duration)
        embed.add_field(name="URL", value=track.uri) if track.uri else "None"
        embed.add_field(
            name="Author", value=track.author
        ) if track.author else ...
        footer = f"Youtube ID: {track.ytid or 'None'} Identifier: {track.identifier or 'None'}"
        embed.set_footer(text=footer)
        return embed

    async def start(self, ctx: commands.Context, song, music):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if not player.is_connected:
            await ctx.invoke(self.connect_)
        if isinstance(song, wavelink.TrackPlaylist):
            for track in song.tracks:
                track = Track(track.id, track.info, requester=ctx.author)
                self.queue.append(track)
            self.now_playing = Track(
                song.tracks[0].id, song.tracks[0].info, requester=ctx.author
            )
            playlist_name = song.data["playlistInfo"]["name"]
            await ctx.send(
                f"Added playlist `{playlist_name}` with `{len(song.tracks)}` songs to the queue. "
            )

        else:
            track = Track(song[0].id, song[0].info, requester=ctx.author)
            self.queue.append(track)
            self.now_playing = track
            await ctx.send(f"Added `{track}` to the queue.")

        await ctx.send(
            embed=self.make_embed(
                ctx,
                Track(
                    self.now_playing.id,
                    self.now_playing.info,
                    requester=ctx.author,
                ),
            ),
            delete_after=10,
        )
        self.queue_position += 1
        await self.play(self.now_playing)
        self.ctx = ctx
        self.started = True

    async def do_next(self):
        if self.no_leave:
            self.queue_position = 0
            song = self.queue[self.queue_position]
        if (
            all(i.bot for i in self.bot.get_channel(self.channel_id).members)
            and not self.no_leave
        ):
            return await self.destory()
        if self.repeat:
            self.queue_position -= 1

        try:
            song = self.queue[self.queue_position]
        except IndexError:
            if self.loop:
                self.queue_position = 0
                song = self.queue[self.queue_position]
            elif not self.is_playing:
                return await self.destroy()

        if song is None:
            return await self.destroy()
        self.queue_position += 1
        self.now_playing = song
        await self.play(song)


class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, "wavelink"):
            self.bot.wavelink = wavelink.Client(bot=self.bot)
            self.bot.wavelink.set_serializer(ujson.dumps)

        self.bot.loop.create_task(self.start_nodes())
        self.bot.url_regex = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            re.IGNORECASE,
        )

    def cog_unload(self):
        self.bot.loop.create_task(self.destroy_players())

    async def destroy_players(self):
        for i in self.bot.wavelink.players.values():
            await i.destroy()

    async def start_nodes(self):
        await self.bot.wait_until_red_ready()

        nodes = {
            "MAIN": {
                "host": "127.0.0.1",
                "port": 2333,
                "rest_uri": "http://127.0.0.1:2333",
                "password": "youshallnotpass",
                "identifier": "MAIN",
                "region": "europe",
            }
        }

        for node in nodes.values():
            await self.bot.wavelink.initiate_node(**node)

    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_node_event_(self, node, event):
        if "YouTube (429)" in event.error:
            player = event.player
            if player.bot.url_regex.fullmatch(player.query):
                new_track = await player.ctx.bot.wavelink.get_tracks(
                    f"scsearch:{player.track.title}"
                )
            else:
                new_track = await player.ctx.bot.wavelink.get_tracks(
                    f"scsearch:{player.query}"
                )
            if new_track:
                track = Track(
                    new_track[0].id,
                    new_track[0].info,
                    requester=player.ctx.author,
                )
                player.queue.append(track)
                player.now_playing = track
                await player.play(player.now_playing)
                await player.ctx.send(
                    embed=player.make_embed(ctx, player.now_playing),
                    delete_after=10,
                )
                await player.ctx.send(
                    "Due to YouTube ratelimiting our IP address, we have searched this song on soundcloud. Please include author name for a more accurate result."
                )
            else:
                await player.ctx.send(
                    "We are so sorry, Youtube has ratelimited us so we can't play anything. We have tried searching on SoundCloud but we can't find anything. Please try a direct link to soundcloud."
                )
        else:
            await event.player.ctx.send(
                f"An error occured while trying to play your music. `{event.error}`"
            )

    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    async def on_node_event(self, node, event):
        await event.player.do_next()

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node):
        print(f" Wavelink node `{node.identifier}` ready.")

    async def cog_check(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("Music commands are not available in DMs.")
            return False

        return True

    async def get_player(self, obj):
        if isinstance(obj, commands.Context):
            return self.wavelink.get_player(
                obj.guild.id, cls=Player, context=obj
            )
        elif isinstance(obj, discord.Guild):
            return self.wavelink.get_player(obj.id, cls=Player)

    @commands.command()
    @commands.is_owner()
    async def node_info(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        node = player.node

        used = humanize.naturalsize(node.stats.memory_used)
        total = humanize.naturalsize(node.stats.memory_allocated)
        free = humanize.naturalsize(node.stats.memory_free)
        cpu = node.stats.cpu_cores

        fmt = (
            f"**WaveLink:** `{wavelink.__version__}`\n\n"
            f"Connected to `{len(self.bot.wavelink.nodes)}` nodes.\n"
            f"Best available Node `{self.bot.wavelink.get_best_node().__repr__()}`\n"
            f"`{len(self.bot.wavelink.players)}` players are distributed on nodes.\n"
            f"`{node.stats.players}` players are distributed on server.\n"
            f"`{node.stats.playing_players}` players are playing on server.\n\n"
            f"Server Memory: `{used}/{total}` | `({free} free)`\n"
            f"Server CPU: `{cpu}`\n\n"
            f"Server Uptime: `{datetime.timedelta(milliseconds=node.stats.uptime)}`"
        )
        await ctx.send(fmt)

    @commands.command()
    async def queue(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        pages = menus.MenuPages(
            source=QueueMenuSource(player.queue[player.queue_position :]),
            delete_message_after=True,
        )
        await pages.start(ctx)

    @commands.command()
    async def selfdeafen(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await self.bot.ws.voice_state(
            player.guild_id, player.channel_id, self_deaf=not player.deafen
        )
        player.deafen = not player.deafen
        await ctx.send("\U0001f44c")

    @commands.command(aliases=["ndc"])
    @commands.is_owner()
    async def nodisconnect(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        player.no_leave = True
        await ctx.send("ok")

    @commands.command(aliases=["np", "currentsong"])
    async def now(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        await ctx.send(embed=player.make_embed(ctx, player.now_playing))

    @commands.command(aliases=["vol"])
    async def volume(self, ctx: commands.Context, volume: int = 100):
        if volume < 0 or volume > 100:
            return await ctx.send("volume must be between 0 to 100")
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.set_volume(volume)
        await ctx.send(f"Volume is now {volume}")

    @commands.command(aliases=["connect"])
    async def join(
        self, ctx: commands.Context, vc: discord.VoiceChannel = None
    ):
        if vc:
            channel = vc
        elif ctx.author.voice:
            channel = ctx.author.voice.channel
        else:
            return await ctx.send("You are not connected to any voice channel")
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.connect(channel.id)
        if isinstance(channel, discord.StageChannel):
            try:
                payload = {"channel_id": channel.id, "suppress": False}
                await self.bot.http.edit_my_voice_state(ctx.guild.id, payload)
            except:
                try:
                    payload = {
                        "channel_id": channel.id,
                        "request_to_speak_timestamp": datetime.datetime.utcnow().isoformat(),
                    }
                    await self.bot.http.edit_my_voice_state(
                        ctx.guild.id, payload
                    )
                except:
                    return await ctx.send(
                        "I need permission to request to speak in stage channel."
                    )
        await ctx.send(f"Connected to {channel.name}")

    @commands.command()
    async def repeat(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if player.repeat:
            player.repeat = False
            return await ctx.send("Unrepeated")
        player.repeat = True
        await ctx.send("Repeating the current song")

    @commands.command()
    async def loop(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if player.loop:
            player.loop = False
            return await ctx.send("Unlooped")
        player.loop = True
        await ctx.send("looped")

    @commands.command()
    async def fastforward(self, ctx: commands.Context, seconds: int):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        seek_position = player.position + (seconds * 1000)
        await player.seek(seek_position)
        await ctx.send(
            f"Fast forwarded {seconds} Current position: {humanize.precisedelta(datetime.timedelta(milliseconds=10))}"
        )

    @commands.command(aliases=["dc", "stop"])
    async def disconnect(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.destroy()
        await ctx.send("disconnected")

    @commands.command()
    async def equalizer(
        self, ctx: commands.Context, name: lambda x: x.lower()
    ):
        equalizers = {
            "none": wavelink.Equalizer.flat(),
            "boost": wavelink.Equalizer.boost(),
            "metal": wavelink.Equalizer.metal(),
            "piano": wavelink.Equalizer.piano(),
        }
        if name not in equalizers:
            return await ctx.send(
                """
                `none` - Resets the equalizer
                `boost` - Boost equalizer. This equalizer emphasizes punchy bass and crisp mid-high tones. Not suitable for tracks with deep/low bass.
                `metal` - Experimental metal/rock equalizer. Expect clipping on bassy songs.
                `piano` - Piano equalizer. Suitable for piano tracks, or tacks with an emphasis on female vocals. Could also be used as a bass cutoff.
                From https://wavelink.readthedocs.io/en/latest/wavelink.html#equalizer
            """
            )

        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.set_eq(equalizers.get(name))
        await player.seek(player.position + 1)
        await ctx.send(f"equalizer setted to {name}")

    @commands.command(name="play")
    async def play_command(self, ctx, *, query: t.Optional[str]):
        player = self.get_player(ctx)

        if not player.is_connected:
            await player.connect(ctx)

        if query is None:
            if player.queue.is_empty:
                raise QueueIsEmpty

            await player.set_pause(False)
            await ctx.send("Playback resumed.")

        else:
            query = query.strip("<>")
            if not re.match(URL_REGEX, query):
                query = f"ytsearch:{query}"

            await player.add_tracks(ctx, await self.wavelink.get_tracks(query))

    @commands.command()
    async def soundcloud(self, ctx, *, music):
        if self.bot.url_regex.fullmatch(music):
            tracks = await self.bot.wavelink.get_tracks(music)
        else:
            tracks = await self.bot.wavelink.get_tracks(f"scsearch:{music}")

        if not tracks:
            return await ctx.send(
                "Could not find any songs with that query. maybe you made a typo?"
            )
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        player.query = music
        if not player.is_connected:
            await ctx.invoke(self.join)
        if not player.started:
            return await player.start(ctx, tracks, music)
        if isinstance(tracks, wavelink.TrackPlaylist):
            for track in tracks.tracks:
                track = Track(track.id, track.info, requester=ctx.author)
                player.queue.append(track)
            playlist_name = tracks.data["playlistInfo"]["name"]
            await ctx.send(
                f"Added playlist `{playlist_name}` with `{len(tracks.tracks)}` songs to the queue. "
            )
        else:
            track = Track(tracks[0].id, tracks[0].info, requester=ctx.author)
            player.queue.append(track)
            await ctx.send(f"Added `{track}` to the queue.")

    @commands.command(aliases=["resume"])
    async def unpause(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if not player.is_paused:
            return await ctx.send("player not paused")
        await player.set_pause(False)
        await ctx.send("unpaused player")

    @commands.command()
    async def skip(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.stop()

    @commands.command()
    async def pause(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if player.is_paused:
            return await ctx.send("player already paused")
        await player.set_pause(True)
        await ctx.send("Paused player")


def setup(bot):
    bot.add_cog(Music(bot))
