# Future Imports
from __future__ import annotations

# Standard Library Imports
from asyncio import TimeoutError as AsyncTimeoutError
from collections import Counter, defaultdict
from io import BytesIO
from random import choice
from typing import Optional
import asyncio
import sys

sys.path.insert(1, "/home/ubuntu/mine/premium")

# Standard Library Imports
import base64
import datetime
import io
import logging
import os
import random
import string
import sys
import time
import urllib

# Dependency Imports
from checks import is_bot_staff, is_premium, premium_tier_checker
from discord.ui import View
from dislash import *
from dislash.interactions import ActionRow, Button, ButtonStyle

# from redbot.core import slash
from redbot import version_info
from redbot.core import commands
from redbot.core.i18n import cog_i18n, Translator
from redbot.core.utils import AsyncIter, chat_formatting as chat
from redbot.core.utils.chat_formatting import (
    bold,
    escape,
    humanize_number,
    humanize_timedelta,
    italics,
    pagify,
)
from redbot.core.utils.predicates import MessagePredicate
from tabulate import tabulate
import aiohttp
import discord
import dislash
import humanize
import psutil
import toml

# Music Imports
from .common_constants import IZUMI_QUOTES
from .config import news, request_log
from .menus.socketstatsmenu import (
    create_counter_chart,
    WSStatsMenu,
    WSStatsPager,
)
from .utils import converters

# from lavalink import all_players


_ = Translator("info", __file__)
log = logging.getLogger("red.mine.izumitools")


# class InfoButton(discord.ui.View):
#    def __init__(self):
#        super().__init__()
#        url='https://izumibot.x10/mx/invite'
#        url1='https://izumibot.x10/mx/support'
#        self.add_item(discord.ui.Button(label='Invite', url='https://izumibot.x10/mx/invite'))
#        self.add_item(discord.ui.Button(label='Support', url='https://izumibot.x10/mx/support', emoji=discord.PartialEmoji(name="pat", animated=True, id="855023907383803945")))


@cog_i18n(_)
class izutools(commands.Cog):
    """general commands for izumi"""

    def cog_unload(self):
        global ping
        global info
        global invite
        global botstats
        if invite:
            try:
                self.bot.remove_command("invite")
            except Exception as e:
                log.info(e)
            self.bot.add_command(invite)
        if ping:
            try:
                self.bot.remove_command("ping")
            except Exception as e:
                log.info(e)
            self.bot.add_command(ping)
        if info:
            try:
                self.bot.remove_command("info")
            except Exception as e:
                log.info(e)
            self.bot.add_command(info)
        if botstats:
            try:
                self.bot.remove_command("botstats")
            except Exception as e:
                log.info(e)
            self.bot.add_command(botstats)
        # This is worse case scenario but still important to check for
        if self.startup_task:
            self.startup_task.cancel()

    @commands.command()
    async def choose(self, ctx, *choices):
        """Choose between multiple options.
        There must be at least 2 options to pick from.
        Options are separated by spaces.
        To denote options which include whitespace, you should enclose the options in double quotes.
        """
        choices = [escape(c, mass_mentions=True) for c in choices if c]
        if len(choices) < 2:
            await ctx.send(_("Not enough options to pick from."))
        else:
            await ctx.send(choice(choices))

    def get_bot_uptime(self):
        # Courtesy of Danny
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if days:
            fmt = f"{days} days, {hours} hours, {minutes} minutes, and {seconds} seconds"
        else:
            fmt = f"{hours} hours, {minutes} minutes, and {seconds} seconds"

        return fmt

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        if not hasattr(bot, "socket_stats"):
            bot.socket_stats = Counter()
        bot.slash = dislash.InteractionClient(bot, modify_send=False)

    # @commands.command(name="screenshot", aliases=["ss"])
    # async def screenshot(ctx, url: str = None):
    #     if url is None:
    #         return await ctx.send(_("Please provide a url to screenshot."))
    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(url) as resp:
    #             if resp.status != 200:
    #                 raise commands.CommandError(f"Could not get screenshot: {resp.status}")

    #             data = await resp.read()

    #     with io.BytesIO(data) as file:
    #         file.seek(0)
    #         await ctx.send(file=discord.File(file, filename="screenshot.png"))

    @commands.Cog.listener()
    async def on_socket_response(self, msg):
        self.bot.socket_stats[msg.get("t", "UNKNOWN") or "UNDEFINED"] += 1

    # @dislash.slash_command(
    #     description="Shows the bot's latency",
    # )
    # @dislash.cooldown(1, 10, commands.BucketType.guild)
    # async def ping(self, inter: dislash.SlashInteraction):
    #     # @commands.command(name="ping", aliases=["pingtime"])
    #     # @commands.max_concurrency(1, commands.BucketType.guild)
    #     # @commands.cooldown(1, 10, commands.BucketType.guild)
    #     # @commands.max_concurrency(1, commands.BucketType.guild)
    #     # async def cmd_ping(self, ctx, show_shards: bool = None):
    #     show_shards = len(
    #         self.bot.latencies) > 1 if show_shards is None else show_shards
    #     latency = self.bot.latency * 1000
    #     is_embed = await ctx.embed_requested()
    #     ping_gifs = (
    #         "https://i1.wp.com/drunkenanimeblog.com/wp-content/uploads/2017/11/shakunetsu-no-takkyuu-musume-scorching-ping-pong-girls.gif?fit=540%2C303&ssl=1&resize=350%2C200",
    #         "https://media1.tenor.com/images/2b27c6e7747d319f76fd98d2a226ab33/tenor.gif?itemid=15479836",
    #         "https://i.gifer.com/6TaL.gif",
    #         "https://remyfool.files.wordpress.com/2016/11/agari-rally.gif?w=924",
    #         "https://4.bp.blogspot.com/-8XanbCQDxfg/WnJTaUeifYI/AAAAAAABEUo/5yv_KUlLV9cmJsuI8jeFRrGSXbtQMclngCKgBGAs/s1600/Omake%2BGif%2BAnime%2B-%2BShokugeki%2Bno%2BSoma%2BS2%2B-%2BOAD%2B1%2B%255BDVD%255D%2B-%2BMegumi%2Bvs%2BIsshiki.gif",
    #         "https://i.kym-cdn.com/photos/images/original/000/753/601/bc8.gif",
    #         "https://i.imgur.com/1cnscjV.gif",
    #         "https://images.squarespace-cdn.com/content/v1/5b23e822f79392038cbd486c/1589129513917-X6QBWRXBHLCSFXT9INR2/b17c1b31e185d12aeca55b576c1ecaef.gif",
    #         "http://i.imgur.com/LkdjWE6.gif",
    #     )
    #     ping_gifs_picker = random.choice(ping_gifs)
    #     quote = random.choice(IZUMI_QUOTES).format(author=ctx.author)
    #     if is_embed:
    #         if show_shards:
    #             # The chances of this in near future is almost 0, but who knows, what future will bring to us?
    #             shards = [_("Shard {}/{}: {}ms").format(shard + 1, self.bot.shard_count,
    #                                                     round(pingt * 1000)) for shard, pingt in self.bot.latencies]
    #         emb = discord.Embed(
    #             title="<a:dancin:862284723710590998>"
    #             if ctx.channel.permissions_for(ctx.me).external_emojis
    #             else _("<a:false:810471052424511498> please enable external emojis"),
    #             color=discord.Color.red(),
    #         )
    #         emb.add_field(
    #             name="Discord WS",
    #             value=chat.box(str(round(latency)) + "ms", "crmsh"),
    #         )
    #         emb.add_field(name=_("Message"), value=chat.box("…", "crmsh"))
    #         emb.set_image(url=ping_gifs_picker)
    #         emb.add_field(name=_("Typing"), value=chat.box("…", "crmsh"))
    #         # Thanks preda, but i copied this from MAX's version
    #         if show_shards:
    #             emb.add_field(name=_("Shards"), value=chat.box(
    #                 "\n".join(shards), "crmsh"))
    #         emb.set_footer(text=quote)

    #         before = time.monotonic()
    #         message = await ctx.reply(embed=emb, mention_author=False)
    #         ping = (time.monotonic() - before) * 1000

    #         emb.colour = await inter.embed_color()
    #         emb.set_field_at(
    #             1,
    #             name=_("Message"),
    #             value=chat.box(
    #                 str(int((message.created_at - (ctx.message.edited_at or ctx.message.created_at)
    #                          ).total_seconds() * 1000)) + "ms",
    #                 "crmsh",
    #             ),
    #         )
    #         emb.set_field_at(2, name=_("Typing"), value=chat.box(
    #             str(round(ping)) + "ms", "crmsh"))

    #         await message.edit(embed=emb)
    #     else:
    #         msg_template = f"{quote}\n{{}}"
    #         table = tabulate(
    #             [
    #                 ("Discord WS", f"{round(latency)}ms"),
    #                 (_("Message"), "…"),
    #                 (_("Typing"), "…"),
    #             ]
    #         )
    #         shards = tabulate(
    #             [
    #                 (
    #                     _("Shard {}/{}").format(shard + 1, self.bot.shard_count),
    #                     f"{round(pingt * 1000)}ms",
    #                 )
    #                 for shard, pingt in self.bot.latencies
    #             ]
    #         )
    #         if show_shards:
    #             table += "\n" + shards
    #         before = time.monotonic()
    #         message = await ctx.reply(msg_template.format(chat.box(table, "crmsh")), mention_author=False)

    #         ping = (time.monotonic() - before) * 1000
    #         table = tabulate(
    #             [
    #                 ("Discord WS", f"{round(latency)}ms"),
    #                 (
    #                     _("Message"),
    #                     f"{int((message.created_at - (ctx.message.edited_at or ctx.message.created_at)).total_seconds() * 1000)}ms",
    #                 ),
    #                 (_("Typing"), f"{round(ping)}ms"),
    #             ]
    #         )
    #         if show_shards:
    #             table += "\n" + shards
    #         await message.edit(content=msg_template.format(chat.box(table, "crmsh")))

    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(
        cls=commands.commands._AlwaysAvailableCommand,
        name="about",
        aliases=["info", "botinfo"],
    )
    async def cmd_about(self, ctx):
        """Info about izumi"""
        #                my_buttons = [
        #            ActionRow(
        #                Button(
        #                    style=ButtonStyle.link,
        #                    label="Invite",
        #                    emoji=discord.PartialEmoji(name="love", animated=False, id="820231241768108044"),
        #                    url="https://izumibot.x10.mx/invite",
        #                ),
        #                Button(
        #                    style=ButtonStyle.link,
        #                    label="Support",
        #                    emoji=discord.PartialEmoji(name="pat", animated=True, id="855023907383803945"),
        #                    url="https://izumibot.x10.mx/support",
        #                ),
        #                Button(
        #                    style=ButtonStyle.link,
        #                    label="BFD - Upvote",
        #                    emoji=discord.PartialEmoji(name="bfdspin", animated=True, id="868769753664208926"),
        #                    url="https://discords.com/bots/bot/762976674659696660/vote",
        #                ),
        #                Button(
        #                    style=ButtonStyle.green,
        #                    label="Donate",
        #                    emoji=discord.PartialEmoji(name="pinksprklehearts", animated=True, id="817568322429124628"),
        #                    custom_id="donate_button",
        #                ),
        #            )
        #        ]
        # timeout_buttons = [
        #     ActionRow(
        #         Button(
        #             style=ButtonStyle.link,
        #             label="Invite",
        #             emoji=discord.PartialEmoji(name="love", animated=False, id="820231241768108044"),
        #             url="https://izumibot.x10.mx/invite",
        #         ),
        #         Button(
        #             style=ButtonStyle.link,
        #             label="Support",
        #             emoji=discord.PartialEmoji(name="pat", animated=True, id="855023907383803945"),
        #             url="https://izumibot.x10.mx/support",
        #         ),
        #         Button(
        #             style=ButtonStyle.link,
        #             label="BFD - Upvote",
        #             emoji=discord.PartialEmoji(name="bfdspin", animated=True, id="868769753664208926"),
        #             url="https://discords.com/bots/bot/762976674659696660/vote",
        #         ),
        #         Button(
        #             style=ButtonStyle.gray,
        #             label="Donate",
        #             emoji=discord.PartialEmoji(name="pinksprklehearts", animated=True, id="817568322429124628"),
        #             custom_id="donate_button",
        #             disabled=True
        #         ),
        #     )
        # ]

        since = datetime.datetime(2020, 10, 6, 9, 0)
        uptime_time = self.get_bot_uptime()
        process = psutil.Process(os.getpid())
        mem = round(process.memory_info()[0] / float(2 ** 20), 2)
        python_url = "https://www.python.org/"
        python_version = "{}.{}.{}".format(*sys.version_info[:3], python_url)
        latency = self.bot.latency * 1000
        ping_b = str(round(latency)) + "ms"
        days_since = (datetime.datetime.utcnow() - since).days
        bot_guilds_1 = humanize_number(len(self.bot.guilds))
        uni_users = humanize_number(len(self.bot.users))
        command_c = len(set(self.bot.walk_commands()))
        channel_c = humanize_number(
            sum(len(s.channels) for s in self.bot.guilds)
        )
        shard_count = humanize_number(self.bot.shard_count)
        shards = _("shards") if self.bot.shard_count > 1 else _("shard")
        visible_users = sum(len(s.members) for s in self.bot.guilds)
        visible_users_1 = humanize_number(visible_users)
        embed = discord.Embed(color=0xF295A4)
        embed.set_thumbnail(
            url=self.bot.user.avatar.with_static_format("png").url
        )
        embed.add_field(
            name=":pushpin: About Izumi:",
            value=(
                "Izumi is a custom [fork](https://github.com/Izumi-DiscordBot/bot) of [Red, an open source Discord bot](https://github.com/Cog-Creators/Red-DiscordBot)\n"
                "(c) Cog Creators\n"
                "It was created by [Twentysix](https://github.com/Cog-Creators/Red-DiscordBot/graphs/contributors) and it is [improved by many](https://github.com/Cog-Creators/Red-DiscordBot/graphs/contributors).\n\n"
                "This fork contains several modifications specific to Izumi into core of Red. "
                "Look at `,credits` for more information."
                "Please do not disturb Red's support channels for any problems/issues about this bot, join my [support server](https://izumibot.x10.mx/support) by using the `,support` command instead."
            ),
            inline=True,
        )
        # embed.add_field(
        #     name="<:stats:872021791256743966> Stats",
        #     value=(
        #         "`{}` Servers • `{}` Users | `{}` Visible Users,\n"
        #         "`{}` {} • `{}` Channels • `{}` Commands,\n"
        #         "Memory: `{}` • Ping `{}`,\n"
        #         "Been up for.. {}"
        #     ).format(
        #         bot_guilds_1,
        #         uni_users,
        #         visible_users_1,
        #         shard_count,
        #         shards,
        #         channel_c,
        #         command_c,
        #         mem,
        #         ping_b,
        #         uptime_time,
        #     ),
        #     inline=False,
        # )
        embed.add_field(
            name=":art: About bot artwork:",
            value="The avatar artwork has been created by [bambieyhs](https://www.deviantart.com/bambieyhs), which you can see the [full version here](https://www.deviantart.com/bambieyhs/art/CM-My-office-is-the-battlefield-767292875), you can look at their [DeviantArt profile](https://www.deviantart.com/bambieyhs).\n A huge thanks to Hyanna and AztoDio, for the previous artworks and a huge thanks for bambieyhs for the current artwork! <:love:820231241768108044>",
            inline=False,
        )
        embed.add_field(
            name="<:bfddev:516837111530258452> Versions:",
            value=f"<:py:821285406547902484> [`{python_version}`]({python_url}) • <:dpy:821284179086016553> [`{discord.__version__}`](https://github.com/Rapptz/discord.py) • <:red:821276871730790420> [`{version_info}`](https://pypi.org/project/Red-DiscordBot)",
            inline=False,
        )
        embed.add_field(
            name=":link: Links:",
            value="[`[BFD  - Upvote]`](https://discords.com/bots/bot/762976674659696660/vote) • [`[Support Server]`](https://izumibot.x10.mx/support) • [`[Invite]`](https://izumibot.x10.mx/invite)",
            inline=False,
        )
        embed.set_footer(
            text="Bringing joy since 06/08/2020 (over {} days ago!)".format(
                days_since
            )
        )
        view = View()
        view.add_item(
            discord.ui.Button(
                label="Invite",
                url="https://izumibot.x10.mx/invite",
                emoji=discord.PartialEmoji(
                    name="love", animated=False, id="820231241768108044"
                ),
            )
        )
        view.add_item(
            discord.ui.Button(
                # style=ButtonStyle.link,
                label="BFD - Upvote",
                emoji=discord.PartialEmoji(
                    name="bfdspin", animated=True, id="868769753664208926"
                ),
                url="https://discords.com/bots/bot/762976674659696660/vote",
            )
        )
        view.add_item(
            discord.ui.Button(
                label="Support",
                url="https://izumibot.x10.mx/support",
                emoji=discord.PartialEmoji(
                    name="pat", animated=True, id="855023907383803945"
                ),
            )
        )

        await ctx.reply(embed=embed, mention_author=False, view=view)

    # @commands.command()
    # @commands.is_owner()
    # async def setup(self, ctx, confirm=False):
    #     if not confirm:
    #         await ctx.send(
    #             "Are you sure you want to register the example slash commands in this guild? "
    #             "Do not do this if they are already registered.\n"
    #             f"Run `{ctx.prefix}setup yes` to confirm."
    #         )
    #         return
    #     payload = {
    #         "name": "command",
    #         "type": 1,
    #         "description": "Example slash command",
    #         "options": [
    #             {
    #                 "name": "member",
    #                 "description": "A discord member",
    #                 "type": 6,
    #                 "required": False,
    #             },
    #         ]
    #     }
    #     payload = {
    #         "name": "invite",
    #         "type": 1,
    #         "description": "Invite Izumi",
    #     }
    #     await self.bot.http.upsert_global_command(self.bot.user.id, payload)
    #     payload = {
    #         "name": "group",
    #         "type": 1,
    #         "description": "Example slash group command",
    #         "options": [
    #             {
    #                 "name": "command",
    #                 "description": "Example slash group command",
    #                 "type": 1,
    #                 "options": [
    #                     {
    #                         "name": "member",
    #                         "description": "A discord member",
    #                         "type": 6,
    #                         "required": False,
    #                     },
    #                 ]
    #             },
    #         ]
    #     }
    #     await self.bot.http.upsert_global_command(self.bot.user.id, payload)
    #     await ctx.tick()

    # @slash.command()
    # async def invite(self, ctx):
    #     """Add me to your server!"""
    #     # invite_buttons = [
    #     #     ActionRow(
    #     #         Button(
    #     #             style=ButtonStyle.link,
    #     #             label="Invite",
    #     #             emoji=discord.PartialEmoji(name="love", animated=False, id="820231241768108044"),
    #     #             url="https://izumibot.x10.mx/invite",
    #     #         ),
    #     #         Button(
    #     #             style=ButtonStyle.link,
    #     #             label="Support",
    #     #             emoji=discord.PartialEmoji(name="pat", animated=True, id="855023907383803945"),
    #     #             url="https://izumibot.x10.mx/support",
    #     #         ),
    #     #     )
    #     # ]
    #     embed = discord.Embed(title="Thanks for using me!", colour=await ctx.embed_colour())
    #     embed.set_thumbnail(url=ctx.me.avatar.with_static_format("png").url)
    #     embed.add_field(
    #         name="Bot Invite",
    #         value=("[Click Here!](https://izumibot.x10.mx/invite)"),
    #         inline=True,
    #     )
    #     embed.add_field(
    #         name="Support Server",
    #         value="[Click Here!](https://izumibot.x10.mx/support)",
    #         inline=True,
    #     )
    #     await ctx.reply(
    #         embed=embed,
    #         # components=invite_buttons,
    #         mention_author=False)

    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.command(name="invite")
    async def cmd_invite(self, ctx):
        """Add me to your server!"""
        # invite_buttons = [
        #     ActionRow(
        #         Button(
        #             style=ButtonStyle.link,
        #             label="Invite",
        #             emoji=discord.PartialEmoji(name="love", animated=False, id="820231241768108044"),
        #             url="https://izumibot.x10.mx/invite",
        #         ),
        #         Button(
        #             style=ButtonStyle.link,
        #             label="Support",
        #             emoji=discord.PartialEmoji(name="pat", animated=True, id="855023907383803945"),
        #             url="https://izumibot.x10.mx/support",
        #         ),
        #     )
        # ]
        embed = discord.Embed(
            title="Thanks for using me!", colour=await ctx.embed_colour()
        )
        embed.set_thumbnail(url=ctx.me.avatar.with_static_format("png").url)
        embed.add_field(
            name="Bot Invite",
            value=("[Click Here!](https://izumibot.x10.mx/invite)"),
            inline=True,
        )
        embed.add_field(
            name="Support Server",
            value="[Click Here!](https://izumibot.x10.mx/support)",
            inline=True,
        )
        await ctx.reply(
            embed=embed,
            # components=invite_buttons,
            mention_author=False,
        )

    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.command()
    async def support(self, ctx):
        """Invite to my support server!"""
        # support_button = [
        #     ActionRow(
        #         Button(
        #             style=ButtonStyle.link,
        #             label="Support",
        #             emoji=discord.PartialEmoji(name="pat", animated=True, id="855023907383803945"),
        #             url="https://izumibot.x10.mx/support",
        #         )
        #     )
        # ]
        embed = discord.Embed(
            title="Thanks for using me!", colour=await ctx.embed_colour()
        )
        embed.set_thumbnail(url=ctx.me.avatar.with_static_format("png").url)
        embed.add_field(
            name="Support server",
            value=(
                "Join [izumi Support](https://izumibot.x10.mx/support) if you need support, have any suggestions, or just want to vibe with us!"
            ),
            inline=True,
        )
        await ctx.reply(
            embed=embed,
            mention_author=False,
            # components=support_button
        )

    @commands.is_owner()
    @commands.command(aliases=["wsstats"], hidden=True)
    @commands.bot_has_permissions(embed_links=True, external_emojis=True)
    async def socketstats(
        self,
        ctx,
        add_chart: bool = False,
    ):
        """WebSocket stats."""
        delta = datetime.datetime.utcnow() - self.bot.uptime
        minutes = delta.total_seconds() / 60
        total = sum(self.bot.socket_stats.values())
        cpm = total / minutes
        chart = None
        if not await self.bot.is_owner(ctx.author):
            add_chart = False
        if add_chart:
            chart = await self.bot.loop.run_in_executor(
                None,
                create_counter_chart,
                self.bot.socket_stats,
                "Socket events",
            )
        await WSStatsMenu(
            WSStatsPager(
                AsyncIter(
                    chat.pagify(
                        tabulate(
                            [
                                (n, chat.humanize_number(v), v / minutes)
                                for n, v in self.bot.socket_stats.most_common()
                            ],
                            headers=["Event", "Count", "APM"],
                            floatfmt=".2f" if add_chart else ".5f",
                        ),
                        page_length=2039,
                    )
                ),
                add_image=add_chart,
            ),
            header=f"{chat.humanize_number(total)} socket events observed (<:apm:841633185854914611> {cpm:.2f}):",
            image=chart,
        ).start(ctx)

    @commands.command(cls=commands.commands._AlwaysAvailableCommand)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def credits(self, ctx):
        """Credits for everyone that makes this bot possible."""
        # my_buttons = [
        #     ActionRow(
        #         Button(
        #             style=ButtonStyle.link,
        #             label="Invite",
        #             emoji=discord.PartialEmoji(name="love", animated=False, id="820231241768108044"),
        #             url="https://izumibot.x10.mx/invite",
        #         ),
        #         Button(
        #             style=ButtonStyle.link,
        #             label="Support",
        #             emoji=discord.PartialEmoji(name="pat", animated=True, id="855023907383803945"),
        #             url="https://izumibot.x10.mx/support",
        #         ),
        #     )
        #        ]
        CONTRIBUTORS = [
            "[**Fixator10**](https://github.com/fixator10/Fixator10-Cogs)",
        ]
        app = await self.bot.application_info()
        repo_cog = self.bot.get_cog("Downloader")
        embed = discord.Embed(
            title=_("{}'s Credits").format(self.bot.user.name),
            description=_(
                "Credits for all people and services that help {} exist."
            ).format(self.bot.user.name),
            timestamp=self.bot.user.created_at,
            color=await self.bot.get_embed_color(None),
        )
        embed.set_footer(text=_("{} exists since").format(self.bot.user.name))
        embed.set_thumbnail(url=str(app.icon.url))
        embed.add_field(
            name="Red-DiscordBot",
            value=_(
                "{} is an instance of [Red bot](https://github.com/Cog-Creators/Red-DiscordBot), "
                "created by [Twentysix](https://github.com/Twentysix26), and maintained by "
                "[awesome community](https://github.com/Cog-Creators/Red-DiscordBot/graphs/contributors)."
            ).format(self.bot.user.name),
            inline=False,
        )
        embed.add_field(
            name=_("Hosting"),
            value=_("This instance is maintained by Onii-chan#3920."),
            inline=False,
        )
        embed.add_field(
            name=_("Art"),
            value=_(
                "The avatar artwork has been created by [bambieyhs](https://www.deviantart.com/bambieyhs),\n"
                "which you can see the [full version here](https://www.deviantart.com/bambieyhs/art/CM-My-office-is-the-battlefield-767292875),\n"
                " you can look at their [DeviantArt profile](https://www.deviantart.com/bambieyhs). A huge thanks to Hyanna and AztoDio, for the previous artworks and a huge thanks for bambieyhs for the current artwork! <:love:820231241768108044>"
            ),
            inline=False,
        )
        used_repos = {c.repo_name for c in await repo_cog.installed_cogs()}
        cogs_credits = _(
            "*Use `{}findcog <command>` to find out who is author of certain command.*\n"
        ).format(ctx.clean_prefix) + "\n".join(
            sorted(
                (
                    f"**[{repo.url.split('/')[4]}]({repo.url})**: {', '.join(repo.author) or repo.url.split('/')[3]}"
                    for repo in repo_cog._repo_manager.repos
                    if repo.url.startswith("http") and repo.name in used_repos
                ),
                key=lambda k: k.title(),
            )
        )
        cogs_credits = list(chat.pagify(cogs_credits, page_length=1024))
        embed.add_field(
            name=_("Third-party modules (Cogs) and their creators"),
            value=cogs_credits[0],
            inline=False,
        )
        cogs_credits.pop(0)
        for page in cogs_credits:
            embed.add_field(
                name="\N{Zero Width Space}", value=page, inline=False
            )
        embed.add_field(
            name=_("Code contributors"),
            value=", ".join(CONTRIBUTORS),
            inline=False,
        )
        embed.add_field(
            name="Special Thanks to",
            value=(
                "[**Fixator10#7133**](https://github.com/fixator10) for sharing a lot of his code and helping (spoonfeeding me a lot of his code) me a lot!\n"
                "[**OufChair**](https://github.com/OofChair) for hosting imgen, a service which helps us make images.\n"
                "[HATSUNE MIKU](https://github.com/Dhruvacube) for helping me with a lot of vote related commands!",
            ),
            inline=False,
        )
        await ctx.reply(
            embed=embed,
            # components=my_buttons,
            mention_author=False,
        )

    # @commands.command(name="disconnectplayers", aliases=["dcplay"])
    # @commands.is_owner()
    # async def command_disconnectplayers(self, ctx):
    #     """Disconnect from all non-playing voice channels."""
    #     stopped_players = [p for p in all_players() if p.current is None]
    #     audio = self.bot.get_cog("Audio")
    #     for player in stopped_players:
    #         if audio and player.channel and player.channel.guild:
    #             await audio.config.guild(player.channel.guild).currently_auto_playing_in.clear()
    #         await player.disconnect()
    #     await ctx.reply(chat.info(f"{len(stopped_players)} inactive players disconnected", mention_author=False))

    @commands.command(name="ping", aliases=["pingtime"])
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def cmd_ping(self, ctx, show_shards: bool = None):
        """Get ping/latency of [botname].
        This data cant be considered an actual latency, and, as matter of fact, affected by many factors.
        Discord WS: WebSocket latency. This is how fast bot will receive events from Discord.
        Message: Difference between your command message and message with ping.
        Typing: Time that bot taken to send message with ping."""
        show_shards = (
            len(self.bot.latencies) > 1 if show_shards is None else show_shards
        )
        latency = self.bot.latency * 1000
        is_embed = await ctx.embed_requested()
        ping_gifs = (
            "https://i1.wp.com/drunkenanimeblog.com/wp-content/uploads/2017/11/shakunetsu-no-takkyuu-musume-scorching-ping-pong-girls.gif?fit=540%2C303&ssl=1&resize=350%2C200",
            "https://media1.tenor.com/images/2b27c6e7747d319f76fd98d2a226ab33/tenor.gif?itemid=15479836",
            "https://i.gifer.com/6TaL.gif",
            "https://remyfool.files.wordpress.com/2016/11/agari-rally.gif?w=924",
            "https://4.bp.blogspot.com/-8XanbCQDxfg/WnJTaUeifYI/AAAAAAABEUo/5yv_KUlLV9cmJsuI8jeFRrGSXbtQMclngCKgBGAs/s1600/Omake%2BGif%2BAnime%2B-%2BShokugeki%2Bno%2BSoma%2BS2%2B-%2BOAD%2B1%2B%255BDVD%255D%2B-%2BMegumi%2Bvs%2BIsshiki.gif",
            "https://i.kym-cdn.com/photos/images/original/000/753/601/bc8.gif",
            "https://i.imgur.com/1cnscjV.gif",
            "https://images.squarespace-cdn.com/content/v1/5b23e822f79392038cbd486c/1589129513917-X6QBWRXBHLCSFXT9INR2/b17c1b31e185d12aeca55b576c1ecaef.gif",
            "http://i.imgur.com/LkdjWE6.gif",
        )
        ping_gifs_picker = random.choice(ping_gifs)
        quote = random.choice(IZUMI_QUOTES).format(author=ctx.author)
        if is_embed:
            if show_shards:
                # The chances of this in near future is almost 0, but who knows, what future will bring to us?
                shards = [
                    _("Shard {}/{}: {}ms").format(
                        shard + 1, self.bot.shard_count, round(pingt * 1000)
                    )
                    for shard, pingt in self.bot.latencies
                ]
            emb = discord.Embed(
                title="<a:dancin:862284723710590998>"
                if ctx.channel.permissions_for(ctx.me).external_emojis
                else _(
                    "<a:false:810471052424511498> please enable external emojis"
                ),
                color=discord.Color.red(),
            )
            emb.add_field(
                name="Discord WS",
                value=chat.box(str(round(latency)) + "ms", "crmsh"),
            )
            emb.add_field(name=_("Message"), value=chat.box("…", "crmsh"))
            emb.set_image(url=ping_gifs_picker)
            emb.add_field(name=_("Typing"), value=chat.box("…", "crmsh"))
            # Thanks preda, but i copied this from MAX's version
            if show_shards:
                emb.add_field(
                    name=_("Shards"),
                    value=chat.box("\n".join(shards), "crmsh"),
                )
            emb.set_footer(text=quote)

            before = time.monotonic()
            message = await ctx.reply(embed=emb, mention_author=False)
            ping = (time.monotonic() - before) * 1000

            emb.colour = await ctx.embed_color()
            emb.set_field_at(
                1,
                name=_("Message"),
                value=chat.box(
                    str(
                        int(
                            (
                                message.created_at
                                - (
                                    ctx.message.edited_at
                                    or ctx.message.created_at
                                )
                            ).total_seconds()
                            * 1000
                        )
                    )
                    + "ms",
                    "crmsh",
                ),
            )
            emb.set_field_at(
                2,
                name=_("Typing"),
                value=chat.box(str(round(ping)) + "ms", "crmsh"),
            )

            await message.edit(embed=emb)
        else:
            msg_template = f"{quote}\n{{}}"
            table = tabulate(
                [
                    ("Discord WS", f"{round(latency)}ms"),
                    (_("Message"), "…"),
                    (_("Typing"), "…"),
                ]
            )
            shards = tabulate(
                [
                    (
                        _("Shard {}/{}").format(
                            shard + 1, self.bot.shard_count
                        ),
                        f"{round(pingt * 1000)}ms",
                    )
                    for shard, pingt in self.bot.latencies
                ]
            )
            if show_shards:
                table += "\n" + shards
            before = time.monotonic()
            message = await ctx.reply(
                msg_template.format(chat.box(table, "crmsh")),
                mention_author=False,
            )

            ping = (time.monotonic() - before) * 1000
            table = tabulate(
                [
                    ("Discord WS", f"{round(latency)}ms"),
                    (
                        _("Message"),
                        f"{int((message.created_at - (ctx.message.edited_at or ctx.message.created_at)).total_seconds() * 1000)}ms",
                    ),
                    (_("Typing"), f"{round(ping)}ms"),
                ]
            )
            if show_shards:
                table += "\n" + shards
            await message.edit(
                content=msg_template.format(chat.box(table, "crmsh"))
            )

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def ship(
        self,
        ctx,
        user1: discord.Member,
        user2: Optional[discord.Member],
        use_nicks: bool = False,
    ):
        """Ship names of 2 server members and count their compatibility level."""
        # thanks flare
        if not user2:
            user2 = ctx.author
            user1, user2 = user2, user1
        if not use_nicks:
            member_name_one = user1.name[: len(user1.name) // 2]
            member_name_two = user2.name[len(user2.name) // 2 :]
        else:
            member_name_one = user1.display_name[
                : len(user1.display_name) // 2
            ]
            member_name_two = user2.display_name[
                len(user2.display_name) // 2 :
            ]
        random.seed(user1.id + user2.id)
        love_level = random.randint(0, 100)
        async with ctx.typing():
            try:
                async with self.session.get(
                    "https://api.martinebot.com/v1/imagesgen/ship",
                    params={
                        "percent": love_level,
                        "first_user": str(
                            user1.avatar.with_static_format("png").url_as(
                                format="png"
                            )
                        ),
                        "second_user": str(
                            user2.avatar.with_static_format("png").url_as(
                                format="png"
                            )
                        ),
                    },
                    raise_for_status=True,
                ) as r:
                    pic = BytesIO(await r.read())
            except aiohttp.ClientResponseError as e:
                pic = _(
                    "Unable to get image: [{e.status}] {e.message}\n\nTry again later."
                ).format(e=e)
            e = discord.Embed(
                title=f"{member_name_one}{member_name_two}",
                description=chat.inline(
                    ("\N{FULL BLOCK}" * round(love_level / 4)).ljust(25)
                )
                + f" {love_level}%",
                color=await ctx.embed_color(),
            )
            if isinstance(pic, BytesIO):
                e.set_image(url="attachment://compatibility.png")
                e.set_footer(
                    text=_("Powered by martinebot.com API"),
                    icon_url="https://cdn.martinebot.com/current/website-assets/avatar.png",
                )
            elif isinstance(pic, str):
                e.set_footer(text=pic)
            await ctx.reply(
                embed=e,
                file=discord.File(pic, filename="compatibility.png")
                if isinstance(pic, BytesIO)
                else None,
            )
            if isinstance(pic, BytesIO):
                pic.close()

    @commands.command(aliases=["si"])
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, external_emojis=True)
    async def serverinfo(self, ctx, guild: discord.Guild = None):
        """
        Show server information.
        """
        if guild is not None and ctx.author.id not in ctx.bot.owner_ids:
            guild = ctx.guild
        if ctx.author.id in ctx.bot.owner_ids:
            guild = guild or ctx.guild
        if guild is None:
            guild = ctx.guild
        created_at = _(
            "Created on **<t:{0}>**. That's **__<t:{0}:R>__**!"
        ).format(
            int(
                guild.created_at.replace(
                    tzinfo=datetime.timezone.utc
                ).timestamp()
            ),
        )
        online = humanize_number(
            len(
                [
                    m.status
                    for m in guild.members
                    if m.status != discord.Status.offline
                ]
            )
        )
        total_users = humanize_number(guild.member_count)
        text_channels = humanize_number(len(guild.text_channels))
        voice_channels = humanize_number(len(guild.voice_channels))
        stage_channels = humanize_number(len(guild.stage_channels))

        def _size(num: int):
            for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
                if abs(num) < 1024.0:
                    return "{0:.1f}{1}".format(num, unit)
                num /= 1024.0
            return "{0:.1f}{1}".format(num, "YB")

        def _bitsize(num: int):
            for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
                if abs(num) < 1000.0:
                    return "{0:.1f}{1}".format(num, unit)
                num /= 1000.0
            return "{0:.1f}{1}".format(num, "YB")

        shard_info = (
            _("\nShard ID: **{shard_id}/{shard_count}**").format(
                shard_id=humanize_number(guild.shard_id + 1),
                shard_count=humanize_number(ctx.bot.shard_count),
            )
            if ctx.bot.shard_count > 1
            else ""
        )
        # Logic from: https://github.com/TrustyJAID/Trusty-cogs/blob/master/serverstats/serverstats.py#L159
        online_stats = {
            _("Humans: "): lambda x: not x.bot,
            _(" • Bots: "): lambda x: x.bot,
            "<a:online:880327962019377153>": lambda x: x.status
            is discord.Status.online,
            "<a:idle:880329216674119710>": lambda x: x.status
            is discord.Status.idle,
            "<a:dnd:880327995573796905>": lambda x: x.status
            is discord.Status.do_not_disturb,
            "<:offline:880332797812830219>": lambda x: (
                x.status is discord.Status.offline
            ),
            "<:streaming:918325738078339103>": lambda x: any(
                a.type is discord.ActivityType.streaming for a in x.activities
            ),
            "<:mobileonline:918326032329764874>": lambda x: x.is_on_mobile(),
        }
        member_msg = _("Users online: **{online}/{total_users}**\n").format(
            online=online, total_users=total_users
        )
        count = 1
        for emoji, value in online_stats.items():
            try:
                num = len([m for m in guild.members if value(m)])
            except Exception as error:
                print(error)
                continue
            else:
                member_msg += f"{emoji} {bold(humanize_number(num))} " + (
                    "\n" if count % 2 == 0 else ""
                )
            count += 1

        vc_regions = {
            "vip-us-east": _("__VIP__ US East ") + "\U0001F1FA\U0001F1F8",
            "vip-us-west": _("__VIP__ US West ") + "\U0001F1FA\U0001F1F8",
            "vip-amsterdam": _("__VIP__ Amsterdam ") + "\U0001F1F3\U0001F1F1",
            "eu-west": _("EU West ") + "\U0001F1EA\U0001F1FA",
            "eu-central": _("EU Central ") + "\U0001F1EA\U0001F1FA",
            "europe": _("Europe ") + "\U0001F1EA\U0001F1FA",
            "london": _("London ") + "\U0001F1EC\U0001F1E7",
            "frankfurt": _("Frankfurt ") + "\U0001F1E9\U0001F1EA",
            "amsterdam": _("Amsterdam ") + "\U0001F1F3\U0001F1F1",
            "us-west": _("US West ") + "\U0001F1FA\U0001F1F8",
            "us-east": _("US East ") + "\U0001F1FA\U0001F1F8",
            "us-south": _("US South ") + "\U0001F1FA\U0001F1F8",
            "us-central": _("US Central ") + "\U0001F1FA\U0001F1F8",
            "singapore": _("Singapore ") + "\U0001F1F8\U0001F1EC",
            "sydney": _("Sydney ") + "\U0001F1E6\U0001F1FA",
            "brazil": _("Brazil ") + "\U0001F1E7\U0001F1F7",
            "hongkong": _("Hong Kong ") + "\U0001F1ED\U0001F1F0",
            "russia": _("Russia ") + "\U0001F1F7\U0001F1FA",
            "japan": _("Japan ") + "\U0001F1EF\U0001F1F5",
            "southafrica": _("South Africa ") + "\U0001F1FF\U0001F1E6",
            "india": _("India ") + "\U0001F1EE\U0001F1F3",
            "dubai": _("Dubai ") + "\U0001F1E6\U0001F1EA",
            "south-korea": _("South Korea ") + "\U0001f1f0\U0001f1f7",
        }
        verif = {
            "none": _("0 - None"),
            "low": _("1 - Low"),
            "medium": _("2 - Medium"),
            "high": _("3 - High"),
            "extreme": _("4 - Extreme"),
        }

        features = {
            "ANIMATED_ICON": _("Animated Icon"),
            "BANNER": _("Banner Image"),
            "COMMERCE": _("Commerce"),
            "COMMUNITY": _("Community"),
            "DISCOVERABLE": _("Server Discovery"),
            "FEATURABLE": _("Featurable"),
            "INVITE_SPLASH": _("Splash Invite"),
            "MEMBER_LIST_DISABLED": _("Member list disabled"),
            "MEMBER_VERIFICATION_GATE_ENABLED": _(
                "Membership Screening enabled"
            ),
            "MORE_EMOJI": _("More Emojis"),
            "NEWS": _("News Channels"),
            "PARTNERED": _("Partnered"),
            "PREVIEW_ENABLED": _("Preview enabled"),
            "PUBLIC_DISABLED": _("Public disabled"),
            "VANITY_URL": _("Vanity URL"),
            "VERIFIED": _("Verified"),
            "VIP_REGIONS": _("VIP Voice Servers"),
            "WELCOME_SCREEN_ENABLED": _("Welcome Screen enabled"),
        }
        guild_features_list = [
            f"<a:check:918326379249020948> {name}"
            for feature, name in features.items()
            if feature in guild.features
        ]

        joined_on = _("I joined this server {since_join} days ago!").format(
            bot_name=ctx.bot.user.name,
            bot_join=guild.me.joined_at.strftime("%d %b %Y %H:%M:%S"),
            since_join=humanize_number(
                (ctx.message.created_at - guild.me.joined_at).days
            ),
        )

        data = discord.Embed(
            description=(
                f"{guild.description}\n\n" if guild.description else ""
            )
            + created_at,
            colour=await ctx.embed_colour(),
        )
        data.set_author(
            name=guild.name,
            icon_url="https://cdn.discordapp.com/emojis/457879292152381443.png"
            if "VERIFIED" in guild.features
            else "https://cdn.discordapp.com/emojis/508929941610430464.png"
            if "PARTNERED" in guild.features
            else discord.Embed.Empty,
        )
        if guild.icon.url:
            data.set_thumbnail(url=guild.icon.url)
        data.add_field(name=_("Members:"), value=member_msg)
        data.add_field(
            name=_("Channels:"),
            value=_(
                "<:text_channel:725390525863034971> Text: {text}\n"
                "<:voice_channel:725390524986425377> Voice: {voice}\n"
                "<:stage_channel_active:848562416328507433> Stage: {stage}"
            ).format(
                text=bold(text_channels),
                voice=bold(voice_channels),
                stage=bold(stage_channels),
            ),
        )
        data.add_field(
            name=_("Utility:"),
            value=_(
                "Owner: {owner}\nVerif. level: {verif}\nServer ID: {id}{shard_info}"
            ).format(
                owner=bold(str(guild.owner)),
                verif=bold(verif[str(guild.verification_level)]),
                id=bold(str(guild.id)),
                shard_info=shard_info,
            ),
            inline=False,
        )
        data.add_field(
            name=_("Misc:"),
            value=_(
                "AFK channel: {afk_chan}\nAFK timeout: {afk_timeout}\nCustom emojis: {emoji_count}\nRoles: {role_count}"
            ).format(
                afk_chan=bold(str(guild.afk_channel))
                if guild.afk_channel
                else bold(_("Not set")),
                afk_timeout=bold(
                    humanize_timedelta(seconds=guild.afk_timeout)
                ),
                emoji_count=bold(humanize_number(len(guild.emojis))),
                role_count=bold(humanize_number(len(guild.roles))),
            ),
            inline=False,
        )
        if guild_features_list:
            data.add_field(
                name=_("Server features:"),
                value="\n".join(guild_features_list),
            )
        if guild.premium_tier != 0:
            nitro_boost = _(
                "Tier {boostlevel} with {nitroboosters} boosts\n"
                "File size limit: {filelimit}\n"
                "Emoji limit: {emojis_limit}\n"
                "VCs max bitrate: {bitrate}"
            ).format(
                boostlevel=bold(str(guild.premium_tier)),
                nitroboosters=bold(
                    humanize_number(guild.premium_subscription_count)
                ),
                filelimit=bold(_size(guild.filesize_limit)),
                emojis_limit=bold(str(guild.emoji_limit)),
                bitrate=bold(_bitsize(guild.bitrate_limit)),
            )
            data.add_field(name=_("Nitro Boost:"), value=nitro_boost)
        if guild.splash:
            data.set_image(url=guild.splash.with_static_format("png").url)
        data.set_footer(text=joined_on)

        await ctx.send(embed=data)

    @commands.command(alias=["bstats"])
    async def botstats(self, ctx):
        "Bot uptime and stuff."

        def percentage_finder(part, whole):
            percentage = 100 * float(part) / float(whole)
            return str(percentage)

        python_process_name = "python"
        java_process_name = "java"
        pid_python = None
        pid_java = None
        for pyproc in psutil.process_iter():
            if python_process_name in pyproc.name():
                pid_python = pyproc.pid
        for jsproc in psutil.process_iter():
            if java_process_name in jsproc.name():
                pid_java = jsproc.pid
        i = await self.bot.application_info()
        latency = self.bot.latency * 1000
        ping_b = str(round(latency)) + "ms"
        channels = 0
        members = 0
        for guild in self.bot.guilds:
            channels += len(guild.text_channels) + len(guild.voice_channels)
        members = sum(s.member_count for s in self.bot.guilds)
        owner = i.owner
        lavalink_process = psutil.Process(pid_java)
        python_process = psutil.Process(pid_python)
        lavalink_memory_usage = lavalink_process.memory_info().rss / 1024 ** 3
        python_memory_usage = python_process.memory_info().rss / 1024 ** 3
        this_pid = os.getpid()
        this_process = psutil.Process(this_pid)
        all_cpu_usage = psutil.cpu_percent()
        bot_cpu_usage = this_process.cpu_percent()

        cpu_usage_percent = psutil.cpu_percent()
        cpu_usage = int(cpu_usage_percent // 10)
        cpu_usage_bar = f"[▰{'▰' * cpu_usage}](https://izumibot.x10.mx/support){'▱' * (10 - cpu_usage)}"
        uptime_time = self.get_bot_uptime()
        servers = len(self.bot.guilds)
        process = psutil.Process()
        mem = process.memory_full_info()
        unique_mem_usage = f"{humanize.naturalsize(mem.uss)}"
        lavalink_tot_mem = lavalink_memory_usage
        python_tot_mem = python_memory_usage
        cpu_count = psutil.cpu_count()
        tot_mem_usage = python_tot_mem + lavalink_tot_mem
        total_mem_usage = "{0:.3f}".format(tot_mem_usage)
        memory = psutil.virtual_memory()
        rounder1 = int(percentage_finder(tot_mem_usage, "8"))
        rounder = rounder1 // 10
        mem_usage_percent = rounder
        mem_usage = int(tot_mem_usage // 10)
        mem_usage_bar = f"[▰{'▰' * mem_usage}](http://dsc.gg/izumisupport){'▱' * (10 - mem_usage)}"
        if not ctx.guild:
            return
        if ctx.guild:
            embed_color = ctx.guild.me.color
        else:
            embed_color = 16753920
        embed = discord.Embed(
            title="Izumi - Stats",
            description=f"[Invite](https://izumibot.x10.mx/invite) | [Support](https://izumibot.x10.mx/support)",
            color=embed_color,
        )

        if ctx.guild.id == 789934742128558080:
            embed.set_thumbnail(
                url="https://fateslist.xyz/api/bots/762976674659696660/widget?format=png&bgcolor=F294A5&textcolor=F2EDDF"
            )
        if ctx.guild.id == 733135938347073576:
            embed.set_image(
                url="https://voidbots.net/api/embed/762976674659696660?theme=light?3971722913"
            )
        else:
            embed.set_image(
                url="https://discords.com/bots/api/bot/762976674659696660/widget"
            )

        embed.set_author(
            name="My statistics:",
            icon_url=self.bot.user.avatar.with_static_format("png").url,
        )
        embed.add_field(name="Owner", value=owner, inline=False)
        embed.add_field(name="Bot ID", value=self.bot.user.id)
        embed.add_field(name="Servers", value=servers)
        embed.add_field(name="Channels", value=channels)
        embed.add_field(name="Users", value=members)
        embed.add_field(name="Uptime", value=uptime_time)
        embed.add_field(name="Ping", value=ping_b)
        embed.add_field(
            name="CPU Usage",
            value=(
                "{} {}%\n"
                "`CPU Cores: 4`\n"
                "`CPU load (bot): {}%`\n"
                "`CPU load (system): {}%`".format(
                    cpu_usage_bar,
                    cpu_usage_percent,
                    bot_cpu_usage,
                    all_cpu_usage,
                )
            ),
        )
        embed.add_field(
            name="RAM Usage",
            value=(
                "{} {}%\n"
                "`Total RAM: 8.0 gb`\n"
                "`Usage (bot): {}`\n"
                "`Usage (all): {} gb`\n"
                "`Usage (Lavalink): {:0.3f} gb`"
            ).format(
                mem_usage_bar,
                mem_usage_percent,
                unique_mem_usage,
                total_mem_usage,
                lavalink_memory_usage,
            ),
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def roles(self, ctx, *, user: converters.Member = None):
        "Check the user's roles. Provide no arguments to check your roles."
        user = user or ctx.author
        desc = "\n".join([r.name for r in user.roles if r.name != "@everyone"])
        if not desc:
            await ctx.send(f"{user} has no roles!")
        else:
            embed = discord.Embed(
                title=f"{user} roles", description=desc, colour=user.color
            )
            await ctx.send(ctx.author.mention, embed=embed)

    @commands.command(
        aliases=["roleperms", "role_permissions", "rolepermissions"]
    )
    @commands.guild_only()
    async def role_perms(self, ctx, *, role: converters.Role):
        "Get role permissions."
        s = []
        for perm, value in role.permissions:
            perm_name = perm.replace("_", " ").replace("Tts", "TTS")
            if not value:
                s.append(f"-{perm_name.title()}: ❌")
            else:
                s.append(f"+{perm_name.title()}: ✅")
        output = "\n".join(s)
        embed = discord.Embed(colour=await ctx.embed_colour())
        embed.add_field(name="Role perms:", value=f"```diff\n{output}\n```")
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="checkpremium")
    async def checkpremium(self, ctx):
        if not ctx.guild:
            return
        if not is_premium:
            return await ctx.send(
                "Oppsie.. Your must be boosting my server to be premium!"
            )
        psince = ctx.author.premium_since
        tier = premium_tier_checker
        if tier == 1:
            tier2 = "Tier 1"
        else:
            tier2 = "Tier 0"

        await ctx.send(
            f"{ctx.author.name} is boosting my support server you have been boosting for {psince} and are {tier2}"
        )

    # @commands.command(name="deadaudio")
    # async def cmd_deaduadio(self, ctx):
    #     msg = (
    #         "__**Izumi's's music feature was removed on the <t:1630677600> (<t:1630677600:R>).**__\n"
    #         "**Learn more about it in the support server https://izumibot.x10.mx/support**\n\n"
    #         "**However, Izumi has a lot more features that might interest you! Check out the bot's help command by running `{}help`!**"
    #     ).format(ctx.prefix)
    #     await ctx.reply(content=msg, mention_author=False)

    @commands.command(
        name="request",
        aliases=[
            "gsuggest",
            "bsuggest",
            "botsuggestion",
        ],
    )
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def _request(self, ctx: commands.Context, *, request):
        """
        Request a feature to be added to Izumi.
        Spamming this command or sending spam requests will get you blacklisted from the bot.
        """
        conf = await ctx.reply(
            f"Are sure you want to send this request?\n> {request}\nReply with y/yes to accept and n/no to deny."
        )
        user = self.bot.get_user(ctx.author.id)

        channel = ctx.channel
        pred = MessagePredicate.yes_or_no(ctx)
        try:
            await self.bot.wait_for("message", check=pred, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.send(
                _("Response timed out, please try again later.")
            )
        if pred.result is True:
            await ctx.send(
                "Your request has been sent!\nThank you for trying to improve Izumi!"
            )
            async with aiohttp.ClientSession() as session:
                request_wh = discord.Webhook.from_url(
                    request_log, session=session
                )
                req_send = discord.Embed(
                    title=f"Request from {str(ctx.author)}",
                    description=f"```{request}```",
                )
                await request_wh.send(
                    embed=req_send,
                    content=f"{ctx.author.id}",
                    username="New Suggestion From - " + ctx.author.name,
                    avatar=ctx.author.avatar.with_static_format("png").url,
                )
                req_embed = discord.Embed(
                    title="Request sent",
                    description=(
                        "Thank you for your request! It has been sent to the support server. "
                        f"Spam will get you permanently blacklisted from {self.bot.user.name}."
                    ),
                )
                req_embed.add_field(
                    name="Your request", value=f"```{request}```"
                )
                req_embed.add_field(
                    name="Contact",
                    value=(
                        "Our staff we contact you when your request is accepted or denied! Keep an eye out on your dms until then!\n"
                        "*- Signed,*\n*Izumi's Staff*"
                    ),
                    inline=False,
                )
                await user.send(embed=req_embed)
        else:
            return await ctx.send("Ok, I'm not sending it!")

    @commands.command(name="breport", alias=["bugreport", "greport"])
    async def _breport(self, ctx):
        """
        Report a bug or User to Izumi's support server.
        """
        components = [
            SelectMenu(
                custom_id="report",
                placeholder="What would you like to report?",
                max_values=1,
                options=[
                    SelectOption("Bug", "Report A bug"),
                    SelectOption("User", "Report A User"),
                ],
            )
        ]
        try:
            await ctx.author.send(
                content="Hello! What would you like to report?",
                components=components,
            )
        except discord.Forbidden:
            return await ctx.send(
                "I can't DM you! Please enable DMs from this server."
            )

    @commands.group()
    @commands.check(is_bot_staff)
    async def rmanage(self, ctx: commands.Context):
        """Manage Requests!"""

    @rmanage.command()
    async def deny(
        self,
        ctx,
        *,
        message_id,
        #        reason,
    ):
        message = message_id

        msg_content = message.content
        msg_embeds = message.embeds

        await ctx.send("msg_content")

    @commands.command(aliases=["oldestmessage"])
    @commands.bot_has_permissions(read_message_history=True, embed_links=True)
    async def firstmessage(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """
        Gets the first message in a channel.
        """
        c = channel if channel else ctx.channel
        first = await c.history(limit=1, oldest_first=True).flatten()
        if first:
            t = "Click here to jump to the first message."
            e = discord.Embed(
                color=await ctx.embed_color(), title=t, url=first[0].jump_url
            )
            await ctx.send(embed=e)
        else:
            await ctx.send("No messages found.")

    # @commands.bot_has_permissions(embed_links=True)
    # @commands.command(aliases=["ship", "lovecalc"])
    # async def lovecalculator(self, ctx, user: discord.User, user2: discord.User = None):
    #     """
    #     Calculates the amount of love between you and the bot.
    #     """
    #     love = random.randint(0, 100)
    #     if user2 is None:
    #         user2 = ctx.author
    #     ua = user.avatar_url_as(static_format="png")
    #     u2a = user2.avatar_url_as(static_format="png")
    #     u = f"https://api.martinebot.com/v1/imagesgen/ship?percent={love}&first_user={ua}&second_user={u2a}&no_69_percent_emoji=false"
    #     t = f"{user.name} and {user2.name} are {love}% in love."
    #     e = discord.Embed(color=await ctx.embed_color(), title=t)
    #     e.set_image(url=u)
    #     e.set_footer(text="Powered by api.martinebot.com")
    #     await ctx.send(embed=e)

    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def country(self, ctx, *, country: str):
        """
        Get info about a specified country.
        """
        safe_country = urllib.parse.quote(country)
        async with self.session.get(
            f"https://restcountries.eu/rest/v2/name/{safe_country}"
        ) as req:
            if req.status == 200:
                data = await req.json()
                name = data[0]["name"]
                capital = data[0]["capital"]
                population = data[0]["population"]
                flag = data[0]["flag"]
                flag_arr = flag.split("/")
                flag_png = (
                    "https://restcountries.com/data/png/" + flag_arr[-1]
                ).replace(".svg", ".png")
                region = data[0]["region"]
                languages = data[0]["languages"]
                langs = []
                for l in languages:
                    langs.append(l["name"])
                langs = ", ".join(langs)
                timezones = data[0]["timezones"]
                e = discord.Embed(color=await ctx.embed_color(), title=name)
                e.add_field(name="Capital", value=capital)
                e.add_field(name="Population", value=f"{population:,}")
                e.add_field(name="Region", value=region)
                e.add_field(name="Languages", value=langs)
                e.add_field(name="Timezones", value=", ".join(timezones))
                e.set_image(url=flag_png)
                await ctx.send(embed=e)
            else:
                await ctx.send("Sorry, I couldn't find that country.")

    @commands.command(
        name="Penis",
        aliases=["pp"],
        description="Displays your penis size, 100% accurate",
    )
    async def _pp(self, ctx, user: discord.User = None):
        await ctx.message.delete()
        if user is None:
            user = ctx.author
        dong = ""
        amount = random.randint(0, 15)
        for i in range(amount):
            dong += "="

        em = discord.Embed(title=f"{user.name}'s cock")
        em.add_field(name="**COCK**", value=f"**8{dong}D**")
        em.set_author(
            name=f"{self.client.user.name}",
            icon_url=f"{self.bot.user.avatar.url}",
        )
        await ctx.send(embed=em, delete_after=60)

    @commands.command(
        name="Otax",
        aliases=["otacks", "tokengrab"],
        description="Fake token grabs a user",
    )
    async def _tokengrab(self, ctx, *, user: discord.User = None):
        await ctx.message.delete()
        if not user:
            user = ctx.author
        userid = str(user.id)
        encodedBytes = base64.b64encode(str(userid).encode("utf-8"))
        encodedid = str(encodedBytes, "utf-8")
        username = user.display_name
        discrim = user.discriminator
        end = ("").join(
            random.choices(
                string.ascii_letters + string.digits + "-" + "_", k=27
            )
        )
        middle = ("").join(
            random.choices(
                string.ascii_letters + string.digits + "-" + "_", k=6
            )
        )

        em1 = discord.Embed(title="Token Decoder")
        em1.add_field(
            name=f"**{username}#{discrim} Base64 encrypted**",
            value=f"```diff\n-{encodedid}```",
        )
        em1.add_field(
            name=f"**{username}#{discrim} Unix Timestamp decrypted**",
            value=f"```diff\n-Calculating...   |```",
        )
        em1.add_field(
            name=f"**{username}#{discrim} HMAC decrypted**",
            value=f"```diff\n-Calculating...   |```",
        )
        em1.add_field(
            name=f"**{username}#{discrim} Full token**",
            value=f"```diff\n-Calculating...   |```",
        )

        em2 = discord.Embed(title="Token Decoder")
        em2.add_field(
            name=f"**{username}#{discrim} Base64 encrypted**",
            value=f"```diff\n-{encodedid}```",
        )
        em2.add_field(
            name=f"**{username}#{discrim} Unix Timestamp decrypted**",
            value=f"```diff\n-Calculating..   /```",
        )
        em2.add_field(
            name=f"**{username}#{discrim} HMAC decrypted**",
            value=f"```diff\n-Calculating..   /```",
        )
        em2.add_field(
            name=f"**{username}#{discrim} Full token**",
            value=f"```diff\n-Calculating..   /```",
        )

        em3 = discord.Embed(title="Token Decoder")
        em3.add_field(
            name=f"**{username}#{discrim} Base64 encrypted**",
            value=f"```diff\n-{encodedid}```",
        )
        em3.add_field(
            name=f"**{username}#{discrim} Unix Timestamp decrypted**",
            value=f"```diff\n-Calculating.   —```",
        )
        em3.add_field(
            name=f"**{username}#{discrim} HMAC decrypted**",
            value=f"```diff\n-Calculating.   —```",
        )
        em3.add_field(
            name=f"**{username}#{discrim} Full token**",
            value=f"```diff\n-Calculating.   —```",
        )

        em4 = discord.Embed(title="Token Decoder")
        em4.add_field(
            name=f"**{username}#{discrim} Base64 encrypted**",
            value=f"```diff\n-{encodedid}```",
        )
        em4.add_field(
            name=f"**{username}#{discrim} Unix Timestamp decrypted**",
            value=f"```diff\n-{middle}```",
        )
        em4.add_field(
            name=f"**{username}#{discrim} HMAC decrypted**",
            value=f"```diff\n-Calculating..   \```",
        )
        em4.add_field(
            name=f"**{username}#{discrim} Full token**",
            value=f"```diff\n-Calculating..   \```",
        )

        em5 = discord.Embed(title="Token Decoder")
        em5.add_field(
            name=f"**{username}#{discrim} Base64 encrypted**",
            value=f"```diff\n-{encodedid}```",
        )
        em5.add_field(
            name=f"**{username}#{discrim} Unix Timestamp decrypted**",
            value=f"```diff\n-{middle}```",
        )
        em5.add_field(
            name=f"**{username}#{discrim} HMAC decrypted**",
            value=f"```diff\n-Calculating...   |```",
        )
        em5.add_field(
            name=f"**{username}#{discrim} Full token**",
            value=f"```diff\n-Calculating...   |```",
        )

        em6 = discord.Embed(title="Token Decoder")
        em6.add_field(
            name=f"**{username}#{discrim} Base64 encrypted**",
            value=f"```diff\n-{encodedid}```",
        )
        em6.add_field(
            name=f"**{username}#{discrim} Unix Timestamp decrypted**",
            value=f"```diff\n-{middle}```",
        )
        em6.add_field(
            name=f"**{username}#{discrim} HMAC decrypted**",
            value=f"```diff\n-Calculating..   /```",
        )
        em6.add_field(
            name=f"**{username}#{discrim} Full token**",
            value=f"```diff\n-Calculating..   /```",
        )

        em7 = discord.Embed(title="Token Decoder")
        em7.add_field(
            name=f"**{username}#{discrim} Base64 encrypted**",
            value=f"```diff\n-{encodedid}```",
        )
        em7.add_field(
            name=f"**{username}#{discrim} Unix Timestamp decrypted**",
            value=f"```diff\n-{middle}```",
        )
        em7.add_field(
            name=f"**{username}#{discrim} HMAC decrypted**",
            value=f"```diff\n-Calculating.   —```",
        )
        em7.add_field(
            name=f"**{username}#{discrim} Full token**",
            value=f"```diff\n-Calculating.   —```",
        )

        em8 = discord.Embed(title="Token Decoder")
        em8.add_field(
            name=f"**{username}#{discrim} Base64 encrypted**",
            value=f"```diff\n-{encodedid}```",
        )
        em8.add_field(
            name=f"**{username}#{discrim} Unix Timestamp decrypted**",
            value=f"```diff\n-{middle}```",
        )
        em8.add_field(
            name=f"**{username}#{discrim} HMAC decrypted**",
            value=f"```diff\n-{end}```",
        )
        em8.add_field(
            name=f"**{username}#{discrim} Full token**",
            value=f"```diff\n-Calculating..   \```",
        )

        final = discord.Embed(title="Token Decoder")
        final.add_field(
            name=f"**{username}#{discrim} Base64 encrypted**",
            value=f"```diff\n-{encodedid}```",
        )
        final.add_field(
            name=f"**{username}#{discrim} Unix Timestamp decrypted**",
            value=f"```diff\n-{middle}```",
        )
        final.add_field(
            name=f"**{username}#{discrim} HMAC decrypted**",
            value=f"```diff\n-{end}```",
        )
        final.add_field(
            name=f"**{username}#{discrim} Full token**",
            value=f"```diff\n+{encodedid}.{middle}.{end}```",
        )

        msg = await ctx.send(embed=em1)
        await asyncio.sleep(1)
        await msg.edit(embed=em2)
        await asyncio.sleep(1)
        await msg.edit(embed=em3)
        await asyncio.sleep(1.2)
        await msg.edit(embed=em4)
        await asyncio.sleep(1.2)
        await msg.edit(embed=em5)
        await asyncio.sleep(1.3)
        await msg.edit(embed=em6)
        await asyncio.sleep(1)
        await msg.edit(embed=em7)
        await asyncio.sleep(1.3)
        await msg.edit(embed=em8)
        await asyncio.sleep(1.3)
        await msg.edit(embed=final, delete_after=60)

    @commands.command(
        name="hack",
        aliases=["funnyhack", "dox"],
        description="Fake doxxes a user",
    )
    async def _hack(self, ctx, user: discord.User):
        try:
            await ctx.message.delete()

        except:
            pass

        name = [
            "James Smith",
            "Michael Smith",
            "Robert Smith",
            "Maria Garcia",
            "David Smith",
            "Maria Rodriguez",
            "Mary Smith",
            "Maria Hernandez",
            "Maria Martinez",
            "James Johnson",
            "Catherine Smoaks",
            "Cindi Emerick",
            "Trudie Peasley",
            "Josie Dowler",
            "Jefferey Amon",
            "Kyung Kernan",
            "Lola Barreiro",
            "Barabara Nuss",
            "Lien Barmore",
            "Donnell Kuhlmann",
            "Geoffrey Torre",
            "Allan Craft",
            "Elvira Lucien",
            "Jeanelle Orem",
            "Shantelle Lige",
            "Chassidy Reinhardt",
            "Adam Delange",
            "Anabel Rini",
            "Delbert Kruse",
            "Celeste Baumeister",
            "Jon Flanary",
            "Danette Uhler",
            "Xochitl Parton",
            "Derek Hetrick",
            "Chasity Hedge",
            "Antonia Gonsoulin",
            "Tod Kinkead",
            "Chastity Lazar",
            "Jazmin Aumick",
            "Janet Slusser",
            "Junita Cagle",
            "Stepanie Blandford",
            "Lang Schaff",
            "Kaila Bier",
            "Ezra Battey",
            "Bart Maddux",
            "Shiloh Raulston",
            "Carrie Kimber",
            "Zack Polite",
            "Marni Larson",
            "Justa Spear",
            "Khabib Bint Khuaylid",
            "Obama bin Hasheem",
            "Osama bin Obama bint Ladin",
            "Jimmy Savill",
            "Sahil Justranch",
            "Retard has no name",
            "Woman so doesn't deserve name",
            "Keith Meh Balls",
            "John Marlow Epstein",
            "Son Goku",
            "Eren Yaegar",
            "Mikasa Ackerman",
            "Son Gohan",
            "Annie Louvehart",
            "Wasim bin Heelda",
            "Jennel Garcia",
            "Robin Parth",
            "Kendrick Lamar",
            "Homo Sapien",
        ]
        location = [
            "Retard lives in his mom's basement LOL",
            "America",
            "United States",
            "Europe",
            "Poland",
            "Mexico",
            "Russia",
            "Pakistan",
            "India",
            "Philipines",
            "Taiwan",
            "China",
            "Japan",
            "North Korea",
            "South Korea",
            "Some random third world country",
            "Canada",
            "Alabama",
            "Alaska",
            "Arizona",
            "Arkansas",
            "California",
            "Colorado",
            "Connecticut",
            "Delaware",
            "Florida",
            "Georgia",
            "Hawaii",
            "Idaho",
            "Illinois",
            "Indiana",
            "Iowa",
            "Kansas",
            "Kentucky",
            "Louisiana",
            "Maine",
            "Maryland",
            "Massachusetts",
            "Michigan",
            "Minnesota",
            "Mississippi",
            "Missouri",
            "Montana",
            "Nebraska",
            "Nevada",
            "New Hampshire",
            "New Jersey",
            "New Mexico",
            "New York",
            "North Carolina",
            "North Dakota",
            "Ohio",
            "Oklahoma",
            "Oregon",
            "Pennsylvania",
            "Rhode Island",
            "South Carolina",
            "South Dakota",
            "Tennessee",
            "Texas",
            "Utah",
            "Vermont",
            "Virginia",
            "Washington",
            "West Virginia",
            "Wisconsin",
            "Wyoming",
            "In your MOM",
            "Cumming",
            "Spain",
            "cOUNTRY WITH BOOM BOOM STICK",
            "BANGLADESH",
            "In the SEA",
            "No home",
            "Gypsy",
            "Homeless fag",
            "Iceland",
            "Greenland",
            "Germany",
            "France",
            "Spain",
            "Portrugal",
        ]
        weight = f"{random.randrange(60,400)} lbs"
        likes = [
            "Gaming",
            "Being a dickhead",
            "Being a bitch",
            "Being cringe",
            "Killing Fags",
            "Being Narcissistic",
            "Living in his mom's basement",
            "Food",
            "Really likes food",
            "Poop",
            "Scat",
            "Sounding",
            "My Little Pony",
        ]
        ethnicity = [
            "White",
            "African American",
            "Asian",
            "THICC Latino",
            "Latina",
            "American",
            "Mexican",
            "Korean",
            "Chinese",
            "Lithuanian",
            "Romanian",
            "Bulgarian",
            "Spaniard",
            "Sexy" "Arab",
            "Italian",
            "Puerto Rican",
            "Non-Hispanic",
            "Russian",
            "Canadian",
            "European",
            "Indian",
            "CHAD bengali",
            "Terrorist",
            "Hindu",
            "ATTACK HELICOPTER",
        ]
        religion = [
            "Christian",
            "Muslim",
            "Atheist",
            "Hindu",
            "Buddhist",
            "Jewish",
            "Pagan",
        ]
        sexuality = [
            "Straight",
            "Gay",
            "Homo",
            "Bi",
            "Bi-Sexual",
            "Lesbian",
            "Pansexual",
            "Mommy",
            "Alabama",
        ]
        education = [
            "High School",
            "College",
            "Middle School",
            "Elementary School",
            "Pre School",
            "Retard never went to school LOL",
            "NASA",
            "Drug Dealer",
        ]
        hair_color = [
            "Black",
            "Brown",
            "Blonde",
            "White",
            "Gray",
            "Red",
            "Blue",
        ]
        # skin_color = ["White", "Pale", "Brown", "Black", "Light-Skin", "Light-Skin Clappers", "Blue", "Yellow", "Simpson"]
        occupation = [
            "Retard has no job LOL",
            "Certified discord retard",
            "Janitor",
            "Police Officer",
            "Teacher",
            "Cashier",
            "Clerk",
            "Waiter",
            "Waitress",
            "Grocery Bagger",
            "Retailer",
            "Sales-Person",
            "Artist",
            "Singer",
            "Rapper",
            "Trapper",
            "Discord Thug",
            "Gangster",
            "Discord Packer",
            "Mechanic",
            "Carpenter",
            "Electrician",
            "Lawyer",
            "Doctor",
            "Programmer",
            "Software Engineer",
            "Scientist",
            "Gets caught by police",
            "Drug dealer",
            "Mom",
            "Woman so has no job",
            "Anime animator",
        ]
        age = random.randrange(1, 100)
        salary = [
            "Retard makes no money LOL",
            "$" + str(random.randrange(0, 1000)),
            "<$50,000",
            "<$75,000",
            "$100,000",
            "$125,000",
            "$150,000",
            "$175,000",
            "$200,000+",
        ]
        email = [
            "@gmail.com",
            "@yahoo.com",
            "@hotmail.com",
            "@outlook.com",
            "@protonmail.com",
            "@disposablemail.com",
            "@aol.com",
            "@edu.com",
            "@icloud.com",
            "@gmx.net",
            "@yandex.com",
        ]
        if user is None:
            em = discord.Embed(title="User cannot be None")
            em.set_author(
                name=f"{self.bot.user.name}",
                icon_url=f"{self.bot.user.avatar.url}",
            )
            await ctx.send(embed=em, delete_after=5)
            return
        if user.id == self.bot.user.id:
            user = ctx.author
            await ctx.send()
        message = await ctx.send(f"`Hacking {user}...\n`")

        # await asyncio.sleep(1)
        # await message.edit(content=f"`Hacking {user}...\nHacking into the mainframe...\n`")
        # await asyncio.sleep(1)
        # await message.edit(content=f"`Hacking {user}...\nHacking into the mainframe...\nCaching data...`")
        # await asyncio.sleep(1)
        # await message.edit(
        #     content=f"`Hacking {user}...\nHacking into the mainframe...\nCaching data...\nCracking SSN information...\n`")
        # await asyncio.sleep(1)
        # await message.edit(
        #     content=f"`Hacking {user}...\nHacking into the mainframe...\nCaching data...\nCracking SSN information...\nBruteforcing love life details...`")
        # await asyncio.sleep(1)
        # await message.edit(
        #     content=f"`Hacking {user}...\nHacking into the mainframe...\nCaching data...\nCracking SSN information...\nBruteforcing love life details...\nFinalizing life-span dox details\n`")
        # await asyncio.sleep(1)
        x = random.randint(1000, 10000)
        texts = [
            "Collecting sensitive information ⚠️ from phishing once done on you... ",
            "Launching Malware ☣️ attacks on you !!",
            "Injecting ransware and pegasus in your system 👾👾 👾 ",
            "Encrypting your important files 🔑🔐.....Making it unreadable to u 🖾🖾🖾",
            "Launching Brute-Force-Attack and adding your ip address to botnets!!! 📍📍📍",
            f"Selling your sensitive data to ha*** 🎭 and got a profit worth {x} dollars 🤑 ",
            f"The dangerous hack has been completed and {user.mention} system has been filled with viruses 💀💀💀!!!",
        ]
        for i in texts:
            await asyncio.sleep(2)
            await message.edit(content=i)

        await message.edit(
            content=(
                f"```Successfully hacked {user}\n"
                f"Name: {random.choice(name)}\n"
                f"Age: {age}\nWeight: {weight}\n"
                f"Location: {random.choice(location)}\n"
                f"Ethnicity: {random.choice(ethnicity)}\n"
                f"Religion: {random.choice(religion)}\n"
                f"Sexuality: {random.choice(sexuality)}\n"
                f"Education: {random.choice(education)}\n"
                f"Occupation: {random.choice(occupation)}\n"
                f"Hair Colour: {random.choice(hair_color)}\n"
                # f"Skin Colour: {random.choice(skin_color)}\n"
                f"Salary: {random.choice(salary)}\n"
                f"Likes: {random.choices(likes, k=3)}\n"
                f"Email: {user.name}@{random.choice(email)}\n```"
            )
        )


def setup(bot):
    cog = izutools(bot)
    global info
    global invite
    global ping
    global botstats

    ping = bot.remove_command("ping")
    info = bot.remove_command("info")
    invite = bot.remove_command("invite")
    botstats = bot.remove_command("botstats")
    bot.add_cog(cog)
