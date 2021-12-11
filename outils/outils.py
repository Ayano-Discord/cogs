# Future Imports
from __future__ import annotations

# Standard Library Imports
from asyncio import TimeoutError as AsyncTimeoutError
from copy import copy
from typing import Optional, Union
import asyncio
import contextlib
import datetime
import logging
import os
import re

# Dependency Imports
from dateutil.parser import parse
from discord import embeds
from dislash.interactions import ActionRow, Button, ButtonStyle
from redbot import json
from redbot.core import commands
from redbot.core.i18n import cog_i18n, Translator
from redbot.core.utils import chat_formatting as chat
from redbot.core.utils.chat_formatting import box, humanize_list
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from tabulate import tabulate
import aiohttp
import discord
import js2py
import psutil

# Music Imports
from .utils import message_logs_channel, news_channels

shutdown: commands.Command = None
restart: commands.Command = None

_ = Translator("Ping", __file__)

LL_JAR_PATH = "/home/ubuntu/izumi_data/cogs/Audio/Lavalink.jar"
log = logging.getLogger("red.mine.outils")
CHANNELS = [
    "general",
    "general-chat",
    "основной",
    "основной-чат",
    "generell",
    "generell-chatt",
    "כללי",
    "צ'אט-כללי",
    "allgemein",
    "generale",
    "général",
    "općenito",
    "bendra",
    "általános",
    "algemeen",
    "generelt",
    "geral",
    "informații generale",
    "ogólny",
    "yleinen",
    "allmänt",
    "allmän-chat",
    "chung",
    "genel",
    "obecné",
    "obično",
    "Генерален чат",
    "общи",
    "загальний",
    "ทั่วไป",
    "常规",
]


class ErrorEmbed(embeds.Embed):
    def __init__(self, **kwargs):
        if "colour" not in kwargs:
            kwargs["colour"] = discord.Color.red()

        super().__init__(**kwargs)


@cog_i18n(_)
class OUtils(commands.Cog):
    """
    Owner utils
    """

    def __init__(self, bot):
        self.session = aiohttp.ClientSession()
        self.bot = bot
        self._statuschannel = None

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())
        global shutdown
        global restart
        if shutdown:
            try:
                self.bot.remove_command("shutdown")
            except Exception as e:
                log.info(e)
            self.bot.add_command(shutdown)
        if restart:
            try:
                self.bot.remove_command("restart")
            except Exception as e:
                log.info(e)
            self.bot.add_command(restart)
        # This is worse case scenario but still important to check for
        if self.startup_task:
            self.startup_task.cancel()

    # @commands.Cog.listener()
    # async def on_message_without_command(self, message: discord.Message):
    #     my_buttons = [
    #         ActionRow(
    #             Button(
    #                 style=ButtonStyle.link,
    #                 label="Support",
    #                 emoji=discord.PartialEmoji(
    #                     name="pat", animated=True, id="855023907383803945"
    #                 ),
    #                 url="https://izumibot.x10.mx/support",
    #             )
    #         )
    #     ]
    #     if message.author.bot:
    #         return
    #     if not message.guild:
    #         return
    #     if not message.channel.permissions_for(message.guild.me).send_messages:
    #         return
    #     if (
    #         await self.bot.allowed_by_whitelist_blacklist(who=message.author)
    #         is False
    #     ):
    #         return
    #     if not re.compile(rf"^<@!?{self.bot.user.id}>$").match(
    #         message.content
    #     ):
    #         return
    #     prefixes = await self.bot.get_prefix(message.channel)
    #     prefixes.remove(f"<@!{self.bot.user.id}> ")
    #     sorted_prefixes = sorted(prefixes, key=len)
    #     if len(sorted_prefixes) > 500:
    #         return
    #     embed = discord.Embed(
    #         colour=await self.bot.get_embed_colour(message.channel),
    #         title="**Hey there!** <a:cappie_excited:818343422921408523>",
    #         description=f"""
    #             ----------\n
    #             My prefixes in this server are {humanize_list(prefixes)}
    #             You can type `{sorted_prefixes[0]}help` to view all commands!\n\n
    #             Need some help? Join my [support server!](https://izumibot.x10.mx/support)
    #             Looking to invite me? [Click here!](https://izumibot.x10.mx/invite)
    #         """,
    #     )
    #     await message.reply(
    #         embed=embed, mention_author=False, components=my_buttons
    #     )

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        my_buttons = [
            ActionRow(
                Button(
                    style=ButtonStyle.link,
                    label="Support",
                    emoji=discord.PartialEmoji(
                        name="pat", animated=True, id="855023907383803945"
                    ),
                    url="https://izumibot.x10.mx/support",
                )
            )
        ]
        if message.author.bot:
            return
        if not message.guild:
            return
        if not message.channel.permissions_for(message.guild.me).send_messages:
            return
        if (
            await self.bot.allowed_by_whitelist_blacklist(who=message.author)
            is False
        ):
            return
        if not re.compile(rf"^<@!?{self.bot.user.id}>$").match(
            message.content
        ):
            return
        prefixes = await self.bot.get_prefix(message.channel)
        if f"<@!{self.bot.user.id}> " in prefixes:
            prefixes.remove(f"<@!{self.bot.user.id}> ")
        sorted_prefixes = sorted(prefixes, key=len)
        if len(sorted_prefixes) > 500:
            return
        embed = discord.Embed(
            colour=await self.bot.get_embed_colour(message.channel),
            title="**Hey there!** <a:cappie_excited:818343422921408523>",
            description=f"""
                ----------\n
                My prefixes in this server are {humanize_list(prefixes)}
                You can type `{sorted_prefixes[0]}help` to view all commands!\n\n
                Need some help? Join my [support server!](https://izumibot.x10.mx/support)
                Looking to invite me? [Click here!](https://izumibot.x10.mx/invite)
            """,
        )
        await message.channel.send(embed=embed)

    @commands.command(name="restart")
    @commands.is_owner()
    async def _restart(self, ctx: commands.Context, silently: bool = False):
        """Attempts to restart [botname].
        Makes [botname] quit with exit code 26.
        The restart is not guaranteed: it must be dealt with by the process manager in use.
        **Examples:**
            - `[p]restart`
            - `[p]restart True` - Restarts silently.
        **Arguments:**
            - `[silently]` - Whether to skip sending the restart message. Defaults to False.
        """

        with contextlib.suppress(discord.HTTPException):
            if not silently:
                await ctx.send(
                    _(
                        "Master, I am restarting now, I'll be back soon! <a:blob_wave:842910347278155817>"
                    )
                )
        await ctx.bot.shutdown(restart=True)

    @commands.command(name="shutdown")
    @commands.is_owner()
    async def _shutdown(self, ctx: commands.Context, silently: bool = False):
        """Shuts down the bot.
        Allows [botname] to shut down gracefully.
        This is the recommended method for shutting down the bot.
        **Examples:**
            - `[p]shutdown`
            - `[p]shutdown True` - Shutdowns silently.
        **Arguments:**
            - `[silently]` - Whether to skip sending the shutdown message. Defaults to False.
        """

        with contextlib.suppress(discord.HTTPException):
            if not silently:
                await ctx.send(
                    _(
                        "Master, I am now shutting down <a:blob_wave:842910347278155817>"
                    )
                )
        await ctx.bot.shutdown()

    @commands.group()
    async def lavalink(self, ctx):
        """Lavalink Updates"""

    @commands.is_owner()
    @lavalink.command(name="freya")
    async def llupdate_freya(self, ctx, version: str = None):
        """Get latest Freya's lavalink build."""
        release_url = (
            f"https://api.github.com/repos/freyacodes/Lavalink/releases/tags{version}"
            if version
            else "https://api.github.com/repos/freyacodes/Lavalink/releases/latest"
        )
        async with ctx.typing():
            async with self.session.get(
                release_url, headers={"Accept": "application/json"}
            ) as r:
                release = await r.json(loads=json.loads)
            if msg := release.get("message"):
                await ctx.reply(
                    chat.error(f"Unable to find release `{version}`: {msg}")
                )
                return
            msg = await ctx.reply(
                chat.warning(
                    "Are you sure that you want to download and install "
                    f"{'pre' if release.get('prerelease') else ''}release {release.get('tag_name', '[No tag]')} "
                    f"(ID: {release.get('id')})?"
                ),
                embed=discord.Embed(
                    description=release.get("body", "No description provided"),
                    color=await ctx.embed_color(),
                    timestamp=parse(release.get("published_at"))
                    if release.get("published_at")
                    else discord.Embed.Empty,
                ),
            )
        if ctx.channel.permissions_for(ctx.me).add_reactions:
            wait, pred = (
                "reaction_add",
                ReactionPredicate.yes_or_no(msg, ctx.author),
            )
            start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
        else:
            wait, pred = "message", MessagePredicate.yes_or_no(ctx)
        try:
            await self.bot.wait_for(wait, check=pred, timeout=30)
        except AsyncTimeoutError:
            pass
        if pred.result:
            async with ctx.typing():
                async with self.session.get(
                    release["assets"][0]["browser_download_url"]
                ) as data:
                    with open(LL_JAR_PATH, "wb") as file:
                        file.write(await data.read())
                await ctx.reply(
                    f"{'Prer' if release.get('prerelease') else 'R'}elease {release.get('tag_name', '[No tag]')} "
                    f"(ID: {release.get('id')}) downloaded. Restart lavalink, by closing and then starting it with java -jar Lavalink.jar -Djdk.tls.client.protocols=TLSv1.2"
                )
        else:
            await ctx.send(chat.info("Canceled"))

    @commands.is_owner()
    @lavalink.command(name="red")
    async def llupdate_red(self, ctx, version: str = None):
        """Get latest Red's lavalink build."""
        release_url = (
            f"https://api.github.com/repos/Cog-Creators/Lavalink-Jars/releases/tags{version}"
            if version
            else "https://api.github.com/repos/Cog-Creators/Lavalink-Jars/releases/latest"
        )
        async with ctx.typing():
            async with self.session.get(
                release_url, headers={"Accept": "application/json"}
            ) as r:
                release = await r.json(loads=json.loads)
            if msg := release.get("message"):
                await ctx.reply(
                    chat.error(f"Unable to find release `{version}`: {msg}")
                )
                return
            msg = await ctx.reply(
                chat.warning(
                    "Are you sure that you want to download and install "
                    f"{'pre' if release.get('prerelease') else ''}release {release.get('tag_name', '[No tag]')} "
                    f"(ID: {release.get('id')})?"
                ),
                embed=discord.Embed(
                    description=release.get("body", "No description provided"),
                    color=await ctx.embed_color(),
                    timestamp=parse(release.get("published_at"))
                    if release.get("published_at")
                    else discord.Embed.Empty,
                ),
            )
        if ctx.channel.permissions_for(ctx.me).add_reactions:
            wait, pred = (
                "reaction_add",
                ReactionPredicate.yes_or_no(msg, ctx.author),
            )
            start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
        else:
            wait, pred = "message", MessagePredicate.yes_or_no(ctx)
        try:
            await self.bot.wait_for(wait, check=pred, timeout=30)
        except AsyncTimeoutError:
            pass
        if pred.result:
            async with ctx.typing():
                async with self.session.get(
                    release["assets"][0]["browser_download_url"]
                ) as data:
                    with open(LL_JAR_PATH, "wb") as file:
                        file.write(await data.read())
                await ctx.reply(
                    f"{'Prer' if release.get('prerelease') else 'R'}elease {release.get('tag_name', '[No tag]')} "
                    f"(ID: {release.get('id')}) downloaded. Restart lavalink, by closing and then starting it with java -jar Lavalink.jar -Djdk.tls.client.protocols=TLSv1.2"
                )
        else:
            await ctx.send(chat.info("Canceled"))

    @property
    def statuschannel(self):
        if not self._statuschannel or isinstance(
            self._statuschannel, discord.Webhook
        ):
            self._statuschannel = self.bot.get_channel(852094131421577218)
        if not self._statuschannel:
            self._statuschannel = discord.Webhook.partial(
                "883598612116942858",
                "5cyWj1aizhshwpwWBTi-TyTc0sdAtTeNVEevajDkXuY7eS7kJweHs6LtzPWvkxB8C3GJ",
                adapter=discord.AsyncWebhookAdapter(self.session),
            )
        return self._statuschannel

    @commands.Cog.listener()
    async def on_connect(self):
        connected = datetime.datetime.utcnow()
        await self.bot.wait_until_red_ready()
        ready = datetime.datetime.utcnow()
        process_start = datetime.datetime.utcfromtimestamp(
            psutil.Process(os.getpid()).create_time()
        )
        after_start = ready - process_start
        embed = discord.Embed(
            title="Connection established",
            description="I'm ready for your commands, Master.",
            color=await self.bot.get_embed_color(self.statuschannel),
        )
        if after_connection := ready - connected:
            embed.add_field(
                name="Prepare time (after connection)",
                value=chat.humanize_timedelta(timedelta=after_connection)
                or f"{after_connection.microseconds} ms",
                inline=False,
            )
        embed.add_field(
            name="Time passed since launch",
            value=chat.humanize_timedelta(timedelta=after_start),
            inline=False,
        )
        await self.statuschannel.send(
            embed=embed,
            # avatar.with_static_format("png").url=self.bot.user.avatar.with_static_format("png").url_as(static_format="png", size=4096),
        )
        await self.session.post(
            "https://ene.fixator10.ru/stats/api/annotations",
            headers={"Authorization": f"Bearer {GRAFANA_API_KEY}"},
            json={
                "dashboardId": 2,
                "panelId": 39,
                "time": int(time() * 1000),
                "tags": ["automated"],
                "text": "Reconnected",
            },
        )

    @commands.command()
    @commands.is_owner()
    async def llversion(self, ctx: commands.Context):
        """Show current lavalink version"""
        async with ctx.typing():
            resp = await asyncio.create_subprocess_exec(
                "java",
                "-jar",
                LL_JAR_PATH,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            results = await resp.communicate()
            if results[1]:
                return await ctx.reply(chat.box(results[1].decode("utf-8")))
            return await ctx.reply(
                chat.box(results[0].decode("utf-8"), lang="py")
            )

    @commands.is_owner()
    @commands.command(aliases=["voiceregions"], hidden=True)
    async def voiceservers(self, ctx: commands.Context):
        """Get list of Discord's voice servers."""
        await ctx.send(
            box(
                tabulate(
                    await self.bot.http.request(
                        discord.http.Route("GET", "/voice/regions")
                    ),
                    headers="keys",
                )
            )
        )

    @commands.command(aliases=["execute"])
    @commands.is_owner()
    async def pipeline(
        self, ctx, make_tasks: Optional[bool] = False, *, cmds: str
    ):
        """Exec multiple commands split by |"""
        for c in cmds.split("|"):
            msg = copy(ctx.message)
            msg.content = ctx.prefix + c.strip()
            to_invoke = self.bot.invoke(await self.bot.get_context(msg))
            self.bot.loop.create_task(
                to_invoke
            ) if make_tasks else await to_invoke
        await ctx.tick()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        try:
            e34 = discord.Embed(
                title=f"{guild.name}",
                color=discord.Color.green(),
                description="Added",
            )
            if guild.icon:
                e34.set_thumbnail(url=guild.icon.url)
            if guild.banner:
                e34.set_image(url=guild.banner.with_format("png").url)
            c = self.bot.get_channel(869016801705615372)
            e34.add_field(name="**Total Members**", value=guild.member_count)
            e34.add_field(
                name="**Bots**",
                value=sum(1 for member in guild.members if member.bot),
            )
            e34.add_field(
                name="**Region**",
                value=str(guild.region).capitalize(),
                inline=True,
            )
            e34.add_field(name="**Server ID**", value=guild.id, inline=True)
            await c.send(
                content=f"We are now currently at **{len(self.bot.guilds)} servers**",
                embed=e34,
            )
        except:
            pass

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        try:
            e34 = ErrorEmbed(title=f"{guild.name}", description="Left")
            if guild.icon:
                e34.set_thumbnail(url=guild.icon.url)
            if guild.banner:
                e34.set_image(url=guild.banner.with_format("png").url)
            c = self.bot.get_channel(869016801705615372)
            e34.add_field(name="**Total Members**", value=guild.member_count)
            e34.add_field(
                name="**Bots**",
                value=sum(1 for member in guild.members if member.bot),
            )
            e34.add_field(
                name="**Region**",
                value=str(guild.region).capitalize(),
                inline=True,
            )
            e34.add_field(name="**Server ID**", value=guild.id, inline=True)
            await c.send(
                content=f"We are now currently at **{len(self.bot.guilds)} servers**",
                embed=e34,
            )
        except:
            pass

    @commands.command()
    @commands.is_owner()
    async def supportunban(
        self,
        ctx: commands.Context,
        user_id: Union[int, discord.User, discord.Member],
        *,
        reason: str = "No reason providen",
    ):
        """Unban a user from Izumi's support server"""
        user = user_id
        if isinstance(user_id, int):
            user = self.bot.get_user(user_id)
            if not user:
                user = await self.bot.fetch_user(user_id)
                if not user:
                    return await ctx.send("Unable to find user!")
        servers = [731147725902708827]
        success = []
        for server in servers:
            server = self.bot.get_guild(server)
            try:
                await server.unban(user, reason=reason)
                success.append(f"**Unbanned in {server.name}**")
            except Exception as e:
                success.append(f"`Unable to unban in {server.name}`: {e}")
        await ctx.send(humanize_list(success))
        await ctx.tick()

    @commands.command(aliases=["bansupport"])
    @commands.is_owner()
    async def supportban(
        self,
        ctx: commands.Context,
        user_id: Union[int, discord.User, discord.Member],
        *,
        reason: str = "No reason providen",
    ):
        """Ban an user from Izumi's support server"""
        user = user_id
        if isinstance(user_id, int):
            user = self.bot.get_user(user_id)
            if not user:
                user = await self.bot.fetch_user(user_id)
                if not user:
                    return await ctx.send("Unable to find user!")
        servers = [852094131047104593]
        success = []
        for server_id in servers:
            server = self.bot.get_guild(server_id)
            try:
                if discord.utils.get(
                    [be.user for be in await server.bans()], id=user_id
                ):
                    success.append(f"**Already banned in my server**")
                    continue
            except Exception as e:
                success.append(
                    "**Cannot get server {serv}**".format(serv=server_id)
                )
            try:
                await server.ban(user, reason=reason)
                success.append(f"**Banned in my server**")
            except Exception as e:
                success.append(f"`Unable to ban in my server: {e}`")
        await ctx.send(humanize_list(success))
        await ctx.tick()

    # @commands.group(invoke_without_command="True")
    # @commands.is_owner()
    # async def owner(self,   ctx):
    #     """Owner management commands"""
    #     if ctx.invoked_subcommand is None:
    #         bois = next(iter(self.bot.owner_ids))
    #         await ctx.send(f"Current Bot Owner IDs:\n{bois}")

    # @owner.command(invoke_without_command="True")
    # @commands.is_owner()
    # async def add(self, ctx, *, user: discord.User):
    #     """Add an owner. Be sure to note that adding the user as an owner will give that user access to everything on your bot. Use this command at your own risk."""
    #     user = self.bot.get_user(user.id)
    #     self.bot.owner_ids.add(user.id)
    #     await ctx.tick()
    #     msg = f"{user.mention} is now a bot owner. Do note that this user currently **has access to everything on the bot, including being able to remove your ownership from the bot.** If you've done this by mistake, please do `{ctx.prefix}owner remove {user.id}` Owners set with this command don't persist during restart. To have a more permanent option, use `redbot instancename --owner {ctx.author.id} --co-owner {user.id}`"
    #     await ctx.send(msg)

    # @owner.command(invoke_without_command="True")
    # @commands.is_owner()
    # async def remove(self, ctx, *, user: discord.User):
    #     """Removes an owner from the bot."""
    #     user=self.bot.get_user(user.id)
    #     self.bot.owner_ids.remove(user.id)
    #     await ctx.tick()
    #     msg=f"{user} is no longer a bot owner."
    #     await ctx.send(msg)

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Listens for news
        """

        channel, guild = message.channel, message.guild

        if not isinstance(message.guild, discord.Guild):
            return
        if channel.id not in news_channels:
            return
        try:
            await asyncio.wait_for(message.publish(), timeout=60)
            log.info(
                "Published message in {} - {}".format(guild.id, channel.name)
            )
            return await self.send_alert_message(
                message=message, alert_type="Success"
            )
        except asyncio.TimeoutError:
            log.info(
                "Failed to publish message in {} - {}".format(
                    guild.id, channel.name
                )
            )
            return await self.send_alert_message(
                message=message, alert_type="HTTPException"
            )

    async def send_alert_message(self, message, alert_type):
        """
        Sends alert if it exists.
        Guild = message.guild
        """
        channel, guild = message.channel, message.guild

        embed = discord.Embed()

        if alert_type == "HTTPException":
            embed.title = "Failed Publish"
            embed.description = "Can't publish [message in {}]({}). Hit 10 publish per user cap.".format(
                channel.mention, message.jump_url
            )

            try:
                return await self.bot.get_channel(message_logs_channel).send(
                    embed=embed
                )
            except discord.Forbidden:
                log.info(
                    "Forbidden. Couldn't send message to {} - {} channel.".format(
                        guild.id, message_logs_channel
                    )
                )

        if alert_type == "Success":
            embed.title = "Success Publish"
            embed.description = "[Published new message in {}.]({})".format(
                channel.mention, message.jump_url
            )

            try:
                return await self.bot.get_channel(message_logs_channel).send(
                    embed=embed
                )
            except discord.Forbidden:
                log.info(
                    "Forbidden. Couldn't send message to {} - {} channel.".format(
                        guild.id, message_logs_channel
                    )
                )

    @commands.command(name="js2py")
    @commands.is_owner()
    async def cmd_js2py(self, ctx, code: str):
        """
        Convert JS to Python
        """
        await ctx.send(js2py.translate_js(code))


def setup(bot):
    cog = OUtils(bot)
    global shutdown
    global restart

    shutdown = bot.remove_command("shutdown")
    restart = bot.remove_command("restart")
    bot.add_cog(cog)
