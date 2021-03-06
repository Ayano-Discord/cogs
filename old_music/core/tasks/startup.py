# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
from collections import namedtuple
from typing import Optional
import asyncio
import itertools
import logging

# Dependency Imports
from redbot.core import Config
from redbot.core.data_manager import cog_data_path
from redbot.core.utils import AsyncIter
from redbot.core.utils._internal_utils import (
    send_to_owners_with_prefix_replaced,
)
from redbot.core.utils.dbtools import APSWConnectionWrapper

# My Modded Imports
from lavalink.filters import Volume
import lavalink

# Music Imports
from ...apis.interface import AudioAPIInterface
from ...apis.playlist_wrapper import PlaylistWrapper
from ...audio_logging import debug_exc_log
from ...errors import DatabaseError, TrackEnqueueError
from ...utils import task_callback
from ..abc import MixinMeta
from ..cog_utils import (
    _OWNER_NOTIFICATION,
    _SCHEMA_VERSION,
    CompositeMetaClass,
)

log = logging.getLogger("red.cogs.Music.cog.Tasks.startup")


class StartUpTasks(MixinMeta, ABC, metaclass=CompositeMetaClass):
    def start_up_task(self):
        # There has to be a task since this requires the bot to be ready
        # If it waits for ready in startup, we cause a deadlock during initial load
        # as initial load happens before the bot can ever be ready.
        lavalink.set_logging_level(self.bot._cli_flags.logging_level)

        if self.is_slash_compatible():
            # Dependency Imports
            from dislash import slash_commands

            if not hasattr(self.bot, "slash"):
                slash_commands.SlashClient(self.bot)
            elif not isinstance(self.bot.slash, slash_commands.SlashClient):
                raise RuntimeError(
                    "Music requires `bot.slash` to be a `SlashClient` object."
                )

        self.cog_init_task = self.bot.loop.create_task(self.initialize())
        self.cog_init_task.add_done_callback(task_callback)

    async def maybe_migrate_from_core(
        self,
    ):  # Copy data from core to new datapath to avoid conflicts.
        if await self.config.migrated_from_core():
            return
        audio_cog_config: Config = Config.get_conf(
            None, 2711759130, cog_name="Audio"
        )
        try:
            audio_cog_config.init_custom("EQUALIZER", 1)
            user_data = await audio_cog_config.all_users()
            member_data = await audio_cog_config.all_members()
            guild_data = await audio_cog_config.all_guilds()
            channel_data = await audio_cog_config.all_channels()
            global_data = await audio_cog_config.all()
            eq_data = await audio_cog_config._get_base_group("EQUALIZER").all()
            await self.config._get_base_group(self.config.GLOBAL).set(
                global_data
            )
            await self.config._get_base_group(self.config.USER).set(user_data)
            await self.config._get_base_group(self.config.MEMBER).set(
                member_data
            )
            await self.config._get_base_group("EQUALIZER").set(eq_data)
            await self.config._get_base_group(self.config.GUILD).set(
                guild_data
            )
            await self.config._get_base_group(self.config.CHANNEL).set(
                channel_data
            )
            await self.config.migrated_from_core.set(True)
        finally:
            # In case this cog is loaded without the core cog being loaded, then unloaded and core cog loaded. this should keep this value same as Core.
            audio_cog_config.force_registration = True

    async def initialize(self) -> None:
        await self.bot.wait_until_red_ready()
        # Unlike most cases, we want the cache to exit before migration.
        try:
            await self.maybe_migrate_from_core()
            await self.maybe_message_all_owners()
            self.db_conn = APSWConnectionWrapper(
                str(cog_data_path(self.bot.get_cog("Music")) / "Audio.db")
            )
            self.api_interface = AudioAPIInterface(
                self.bot,
                self.config,
                self.session,
                self.db_conn,
                self.bot.get_cog("Music"),
                self.config_cache,
            )
            self.playlist_api = PlaylistWrapper(
                self.bot, self.config, self.db_conn, self.config_cache
            )
            await self.playlist_api.init()
            await self.api_interface.initialize()
            self.global_api_user = (
                await self.api_interface.global_cache_api.get_perms()
            )
            await self.data_schema_migration(
                from_version=await self.config.schema_version(),
                to_version=_SCHEMA_VERSION,
            )
            await self.playlist_api.delete_scheduled()
            await self.api_interface.persistent_queue_api.delete_scheduled()
            await self._build_bundled_playlist()
            self.lavalink_restart_connect()
            self.player_automated_timer_task = self.bot.loop.create_task(
                self.player_automated_timer()
            )
            self.player_automated_timer_task.add_done_callback(task_callback)
        except Exception as err:
            log.exception(
                "Music failed to start up, please report this issue.",
                exc_info=err,
            )
            raise err

        self.cog_ready_event.set()

    async def restore_players(self):
        tries = 0
        tracks_to_restore = (
            await self.api_interface.persistent_queue_api.fetch_all()
        )
        while not lavalink.node._nodes:
            await asyncio.sleep(1)
            tries += 1
            if tries > 60:
                log.exception(
                    "Unable to restore players, couldn't connect to Lavalink."
                )
                return
        metadata = {}
        all_guilds = await self.config.all_guilds()
        ctx = namedtuple("Context", "guild")
        async for guild_id, guild_data in AsyncIter(
            all_guilds.items(), steps=100
        ):
            if (
                guild_data["auto_play"]
                and guild_data["currently_auto_playing_in"]
            ):
                notify_channel, vc_id = guild_data["currently_auto_playing_in"]
                metadata[guild_id] = (notify_channel, vc_id)

        for guild_id, track_data in itertools.groupby(
            tracks_to_restore, key=lambda x: x.guild_id
        ):
            await asyncio.sleep(0)
            tries = 0
            try:
                player: Optional[lavalink.Player] = None
                track_data = list(track_data)
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue
                persist_cache = (
                    await self.config_cache.persistent_queue.get_context_value(
                        guild
                    )
                )
                if not persist_cache:
                    await self.api_interface.persistent_queue_api.drop(
                        guild_id
                    )
                    continue
                if self.lavalink_connection_aborted:
                    player = None
                else:
                    try:
                        player = lavalink.get_player(guild_id)
                    except IndexError:
                        player = None
                    except KeyError:
                        player = None
                vc = 0
                shuffle = await self.config_cache.shuffle.get_context_value(
                    guild
                )
                repeat = await self.config_cache.repeat.get_context_value(
                    guild
                )
                shuffle_bumped = (
                    await self.config_cache.shuffle_bumped.get_context_value(
                        guild
                    )
                )
                auto_deafen = (
                    await self.config_cache.auto_deafen.get_context_value(
                        guild
                    )
                )

                if player is None:
                    while tries < 5 and vc is not None:
                        try:
                            notify_channel_id, vc_id = metadata.pop(
                                guild_id, (None, track_data[-1].room_id)
                            )
                            vc = guild.get_channel(vc_id)
                            if not vc:
                                break
                            perms = vc.permissions_for(guild.me)
                            if not (perms.connect and perms.speak):
                                vc = None
                                break
                            player = await lavalink.connect(
                                vc, deafen=auto_deafen
                            )
                            player.store("notify_channel", notify_channel_id)
                            break
                        except IndexError:
                            await asyncio.sleep(5)
                            tries += 1
                        except Exception as exc:
                            tries += 1
                            debug_exc_log(
                                log,
                                exc,
                                "Failed to restore music voice channel %s",
                                vc_id,
                            )
                            if vc is None:
                                break
                            else:
                                await asyncio.sleep(1)

                if tries >= 5 or guild is None or vc is None or player is None:
                    await self.api_interface.persistent_queue_api.drop(
                        guild_id
                    )
                    continue

                volume = Volume(
                    value=await self.config_cache.volume.get_context_value(
                        guild, channel=player.channel
                    )
                    / 100
                )
                player.repeat = repeat
                player.shuffle = shuffle
                player.shuffle_bumped = shuffle_bumped
                if player.volume != volume:
                    await player.set_volume(volume)
                await self._eq_check(player=player, ctx=ctx(guild))
                for track in track_data:
                    track = track.track_object
                    player.add(
                        guild.get_member(track.extras.get("requester"))
                        or guild.me,
                        track,
                    )
                player.maybe_shuffle()
                if not player.is_playing:
                    await player.play()
                log.info("Restored %r", player)
            except Exception as err:
                debug_exc_log(
                    log, err, "Error restoring player in %d", guild_id
                )
                await self.api_interface.persistent_queue_api.drop(guild_id)

        for guild_id, (notify_channel_id, vc_id) in metadata.items():
            guild = self.bot.get_guild(guild_id)
            player: Optional[lavalink.Player] = None
            vc = 0
            tries = 0
            if not guild:
                continue
            if self.lavalink_connection_aborted:
                player = None
            else:
                try:
                    player = lavalink.get_player(guild_id)
                except IndexError:
                    player = None
                except KeyError:
                    player = None
            if player is None:
                shuffle = await self.config_cache.shuffle.get_context_value(
                    guild
                )
                repeat = await self.config_cache.repeat.get_context_value(
                    guild
                )
                shuffle_bumped = (
                    await self.config_cache.shuffle_bumped.get_context_value(
                        guild
                    )
                )
                auto_deafen = (
                    await self.config_cache.auto_deafen.get_context_value(
                        guild
                    )
                )

                while tries < 5 and vc is not None:
                    try:
                        vc = guild.get_channel(vc_id)
                        if not vc:
                            break
                        perms = vc.permissions_for(guild.me)
                        if not (perms.connect and perms.speak):
                            vc = None
                            break
                        player = await lavalink.connect(vc, deafen=auto_deafen)
                        player.store("notify_channel", notify_channel_id)
                        break
                    except IndexError:
                        await asyncio.sleep(5)
                        tries += 1
                    except Exception as exc:
                        tries += 1
                        debug_exc_log(
                            log,
                            exc,
                            "Failed to restore music voice channel %s",
                            vc_id,
                        )
                        if vc is None:
                            break
                        else:
                            await asyncio.sleep(1)
                if tries >= 5 or guild is None or vc is None or player is None:
                    continue

                volume = Volume(
                    value=await self.config_cache.volume.get_context_value(
                        guild, channel=player.channel
                    )
                    / 100
                )
                player.repeat = repeat
                player.shuffle = shuffle
                player.shuffle_bumped = shuffle_bumped
                if player.volume != volume:
                    await player.set_volume(volume)
                await self._eq_check(player=player, ctx=ctx(guild))
                player.maybe_shuffle()
                log.info("Restored %r", player)
                if not player.is_playing:
                    notify_channel = player.fetch("notify_channel")
                    try:
                        await self.api_interface.autoplay(
                            player, self.playlist_api
                        )
                    except DatabaseError:
                        notify_channel = self.bot.get_channel(notify_channel)
                        if notify_channel:
                            await self.send_embed_msg(
                                notify_channel,
                                title="Couldn't get a valid track.",
                            )
                        return
                    except TrackEnqueueError:
                        notify_channel = self.bot.get_channel(notify_channel)
                        if notify_channel:
                            await self.send_embed_msg(
                                notify_channel,
                                title="Unable to Get Track",
                                description=(
                                    "I'm unable to get a track from Lavalink at the moment, "
                                    "try again in a few minutes."
                                ),
                            )
                        return
        del metadata
        del all_guilds

    async def maybe_message_all_owners(self):
        current_notification = await self.config.owner_notification()
        if current_notification == _OWNER_NOTIFICATION:
            return
        if current_notification < 1 <= _OWNER_NOTIFICATION:
            msg = """Hello, this message brings you an important update regarding the core Music cog:

Starting from Music v2.3.0+ you can take advantage of the **Global Audio API**, a new service offered by the Cog-Creators organization that allows your bot to greatly reduce the amount of requests done to YouTube / Spotify. This reduces the likelihood of YouTube rate-limiting your bot for making requests too often.
See `[p]help audioset global globalapi` for more information.
Access to this service is disabled by default and **requires you to explicitly opt-in** to start using it.

An access token is **required** to use this API. To obtain this token you may join <https://discord.gg/red> and run `?audioapi register` in the #testing channel.
Note: by using this service you accept that your bot's IP address will be disclosed to the Cog-Creators organization and used only for the purpose of providing the Global API service.

On a related note, it is highly recommended that you enable your local cache if you haven't yet.
To do so, run `[p]audioset global cache 5`. This cache, which stores only metadata, will make repeated audio requests faster and further reduce the likelihood of YouTube rate-limiting your bot. Since it's only metadata the required disk space for this cache is expected to be negligible."""
            await send_to_owners_with_prefix_replaced(self.bot, msg)
            await self.config.owner_notification.set(1)
