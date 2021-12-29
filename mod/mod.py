# Future Imports
from __future__ import annotations

# Standard Library Imports
from datetime import timezone
import datetime
import os
import sys

# Dependency Imports
from discord.ui import View
from dislash import *
from dislash.interactions.application_command import *
from redbot import version_info
from redbot.cogs.mod import Mod as ModClass
from redbot.cogs.mod.mod import _
from redbot.core import commands
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import (
    bold,
    humanize_number,
    humanize_timedelta,
)
from redbot.core.utils.common_filters import filter_invites
import aiohttp
import discord
import dislash
import humanize
import psutil

EMOJIS = {
    "staff": 848556248832016384,
    "early_supporter": 706198530837970998,
    "hypesquad_balance": 706198531538550886,
    "hypesquad_bravery": 706198532998299779,
    "hypesquad_brilliance": 706198535846101092,
    "hypesquad": 706198537049866261,
    "verified_bot_developer": 706198727953612901,
    "bug_hunter": 848556247632052225,
    "bug_hunter_level_2": 706199712402898985,
    "partner": 750454680198578389,
    "verified_bot": 848561838974697532,
    "verified_bot2": 848561839260434482,
    # NONFLAGS
    "booster": 710871139227795487,
    "owner": 725387683811033140,
    "bot": 848557763172892722,
}

STATUS_EMOJIS = {
    "mobile": 749067110931759185,
    "online": 880327962019377153,
    "offline": 880332797812830219,
    "away": 880329216674119710,
    "dnd": 880327995573796905,
    "streaming": 749221434039205909,
}

SPECIAL_BADGES = {
    852094131047104593: {  # izumi Support
        852094131047104600: 516837111530258452,  # RED
        852094131231522818: 506624224723730462,  # Admin
        852094131231522817: 613924521883205635,  # Mod
        852094131231522819: 506624306252349452,  # Developer
        873788122926813245: 510569579982880790,  # Trusted
        869063620829528115: 510974232855838730,  # Premium
        859318529701183508: 706199712402898985,  # Bug Hunter
    },
    133049272517001216: {  # Red
        346744009458450433: 895213558789468210,  # Contributor
    },
    240154543684321280: {  # Cog Support
        529359322140901377: 594238096934043658,  # Cog Creator
    },
}


class RouteV9(discord.http.Route):
    BASE = "https://canary.discord.com/api/v9"


class Mod(ModClass):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, external_emojis=True)
    async def userinfo(self, ctx, *, user: discord.Member = None):
        """Show information about a user.

        This includes fields for status, discord join date, server
        join date, voice state and previous names/nicknames.
        If the user has no roles, previous names or previous nicknames,
        these fields will be omitted.
        """
        await ctx.trigger_typing()
        author = ctx.author
        guild = ctx.guild

        if not user:
            user = author

        roles = user.roles[-1:0:-1]
        names, nicks = await self.get_names_and_nicks(user)
        dt = user.joined_at
        dt1 = user.created_at
        unix_ts_utc = dt.replace(tzinfo=timezone.utc).timestamp()
        unix_ts_utc1 = dt1.replace(tzinfo=timezone.utc).timestamp()
        user_c_converter = int(unix_ts_utc1)
        user_j_converter = int(unix_ts_utc)

        since_created = "<t:{}:R>".format(user_c_converter)
        if user.joined_at is not None:
            since_joined = "<t:{}:R>".format(user_j_converter)
            user_joined = "<t:{}>".format(user_j_converter)
        else:
            since_joined = "?"
            user_joined = _("Unknown")
        user_created = "<t:{}>".format(user_c_converter)
        voice_state = user.voice
        member_number = (
            sorted(
                guild.members,
                key=lambda m: m.joined_at or ctx.message.created_at,
            ).index(user)
            + 1
        )

        sharedguilds = (
            user.mutual_guilds
            if hasattr(user, "mutual_guilds")
            else {
                guild
                async for guild in AsyncIter(self.bot.guilds, steps=100)
                if user in guild.members
            }
        )

        created_on = _("{} - ({})\n").format(since_created, user_created)
        joined_on = _("{} - ({})\n").format(since_joined, user_joined)

        if user.is_on_mobile():
            statusemoji = (
                self.bot.get_emoji(STATUS_EMOJIS["mobile"])
                or "\N{MOBILE PHONE}"
            )
        elif any(
            a.type is discord.ActivityType.streaming for a in user.activities
        ):
            statusemoji = (
                self.bot.get_emoji(STATUS_EMOJIS["streaming"])
                or "\N{LARGE PURPLE CIRCLE}"
            )
        elif user.status.name == "online":
            statusemoji = (
                self.bot.get_emoji(STATUS_EMOJIS["online"])
                or "\N{LARGE GREEN CIRCLE}"
            )
        elif user.status.name == "offline":
            statusemoji = (
                self.bot.get_emoji(STATUS_EMOJIS["offline"])
                or "\N{MEDIUM WHITE CIRCLE}"
            )
        elif user.status.name == "dnd":
            statusemoji = (
                self.bot.get_emoji(STATUS_EMOJIS["dnd"])
                or "\N{LARGE RED CIRCLE}"
            )
        elif user.status.name == "idle":
            statusemoji = (
                self.bot.get_emoji(STATUS_EMOJIS["away"])
                or "\N{LARGE ORANGE CIRCLE}"
            )
        else:
            statusemoji = MISSING_EMOJI
        activity = _("**Chilling in {} status**").format(user.status)
        status_string = self.get_status_string(user)

        if roles:

            role_str = ", ".join([x.mention for x in roles])
            # 400 BAD REQUEST (error code: 50035): Invalid Form Body
            # In embed.fields.2.value: Must be 1024 or fewer in length.
            if len(role_str) > 1024:
                # Alternative string building time.
                # This is not the most optimal, but if you're hitting this, you are losing more time
                # to every single check running on users than the occasional user info invoke
                # We don't start by building this way, since the number of times we hit this should be
                # infintesimally small compared to when we don't across all uses of Red.
                continuation_string = _(
                    "and {numeric_number} more roles not displayed due to embed limits."
                )

                available_length = 1024 - len(
                    continuation_string
                )  # do not attempt to tweak, i18n

                role_chunks = []
                remaining_roles = 0

                for r in roles:
                    chunk = f"{r.mention}, "
                    chunk_size = len(chunk)

                    if chunk_size < available_length:
                        available_length -= chunk_size
                        role_chunks.append(chunk)
                    else:
                        remaining_roles += 1

                role_chunks.append(
                    continuation_string.format(numeric_number=remaining_roles)
                )

                role_str = "".join(role_chunks)

        else:
            role_str = None

        stoa = status_string or activity + "\n"
        l_sharedg = len(sharedguilds)

        data_r = await self.bot.http.request(
            RouteV9("GET", f"/users/{user.id}")
        )

        dg_id = data_r.get("id")
        dg_username = data_r.get("username")
        dg_discriminator = data_r.get("discriminator")

        if data_r.get("banner") != None:
            banner_hash = data_r.get("banner")
            animated = banner_hash.startswith("a_")
            extension = "gif" if animated else "png"
            banner_url = (
                "https://cdn.discordapp.com/banners/{}/{}.{}?size=4096".format(
                    user.id, banner_hash, extension
                )
            )

        else:
            banner_url = ""

        data = discord.Embed(colour=user.colour)

        if names:
            name_name = (
                _("**Previous Names:**")
                if len(names) > 1
                else _("**Previous Name:**")
            )
            name_val = filter_invites(", ".join(names))
            prev_names_val = "{}\n{}".format(
                name_name,
                name_val,
            )

        else:
            prev_names_val = ""

        data.set_image(url=banner_url)

        data.add_field(
            name=_("__User Info__"),
            value=_(
                "**Shared Servers:** {}\n" "**Joined Discord:** {}" "{}" "{}"
            ).format(
                l_sharedg,
                created_on,
                stoa,
                prev_names_val,
            ),
            inline=False,
        )

        if nicks:
            nick_name = (
                _("**Previous Nicknames:**")
                if len(nicks) > 1
                else _("**Previous Nickname:**")
            )
            nick_val = filter_invites(", ".join(nicks))
            prev_nicks_val = "{}\n{}\n".format(
                nick_name,
                nick_val,
            )

        else:
            prev_nicks_val = ""

        if role_str is not None:
            role_name = _("**Roles:**") if len(roles) > 1 else _("**Role:**")
            role_val = role_str
            prev_rol_val = "{}\n{}\n".format(
                role_name,
                role_val,
            )

        else:
            prev_rol_val = "This person doesn't seem to have any roles."

        if voice_state and voice_state.channel:
            voice_name = _("Current voice channel:")
            voice_val = "{0.mention} ID: {0.id}".format(voice_state.channel)
            prev_voice_val = "{} {}".format(
                voice_name,
                voice_val,
            )

        else:
            prev_voice_val = ""

        data.add_field(
            name=_("__Member info__"),
            value=_("**Joined this server:** {}" "{}" "{}" "{}").format(
                joined_on,
                prev_nicks_val,
                prev_rol_val,
                prev_voice_val,
            ),
            inline=False,
        )

        name = str(user)
        name = " ~ ".join((name, user.nick)) if user.nick else name
        name = discord.utils.escape_markdown(
            filter_invites(name), as_needed=True
        )
        avatar = user.avatar.with_static_format("png").url
        guild_badges = []
        badges = []
        flags = [f.name for f in user.public_flags.all()]
        if guild.owner == user:
            guild_badges.append(
                str(self.bot.get_emoji(EMOJIS.get("owner"))) or MISSING_EMOJI
            )
        if user.premium_since:
            guild_badges.append(
                str(self.bot.get_emoji(EMOJIS.get("booster"))) or MISSING_EMOJI
            )
        if user.bot and "verified_bot" not in flags:
            badges.append(
                str(self.bot.get_emoji(EMOJIS.get("bot"))) or MISSING_EMOJI
            )
        for badge in sorted(flags):
            if badge == "verified_bot":
                badges.append(str(self.bot.get_emoji(EMOJIS["verified_bot"])))
                badges.append(str(self.bot.get_emoji(EMOJIS["verified_bot2"])))
                continue
            badges.append(
                str(self.bot.get_emoji(EMOJIS.get(badge)) or MISSING_EMOJI)
            )
        data.title = (
            f"{statusemoji} {name} {''.join(guild_badges)} {''.join(badges)}"
        )
        if len(data.title) > 256:
            data.title = f"{statusemoji} {name} {''.join(guild_badges)}"
            data.description = "".join(badges) + "\n" + data.description
        data.set_thumbnail(url=avatar)

        if not user.bot:
            special_badges = []
            for guild_id, roles in SPECIAL_BADGES.items():
                if (guild := self.bot.get_guild(guild_id)) and (
                    special_member := guild.get_member(user.id)
                ):
                    for r in reversed(special_member.roles):
                        if r.id in roles:
                            special_badges.append(
                                f"{self.bot.get_emoji(roles[r.id])} {r.name}"
                            )
            if special_badges:
                data.add_field(
                    name="Special Badges:", value="\n".join(special_badges)
                )
        member_number = (
            sorted(
                ctx.guild.members,
                key=lambda m: m.joined_at or ctx.message.created_at,
            ).index(user)
            + 1
        )
        data.set_footer(
            text="Member: #{} • User Id: {}".format(
                member_number,
                dg_id,
            )
        )
        await ctx.reply(embed=data, mention_author=False)

    @dislash.guild_only()
    @slash_command(
        description="Get info about yourself, other users or the server!"
    )
    async def info(self, inter):
        pass

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

    #    @commands.cooldown(1, 10, commands.BucketType.user)
    @info.sub_command(name="bot", description="Info About Hibiki")
    async def slash_about(self, inter):
        """Info about Hibiki"""
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
        #        python_url = "https://www.python.org"
        python_version = "[{}.{}.{}]".format(
            *sys.version_info[:3],
        )
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
        embed = discord.Embed(color=0xE2CFC6)
        embed.set_thumbnail(
            url=self.bot.user.avatar.with_static_format("png").url
        )
        embed.add_field(
            name=":pushpin: About Hibiki:",
            value=(
                "Hibiki is a custom fork of [Red, an open source Discord bot](https://github.com/Cog-Creators/Red-DiscordBot)\n"
                "(c) Cog Creators\n"
                "It was created by [Twentysix](https://github.com/Cog-Creators/Red-DiscordBot/graphs/contributors) and it is [improved by many](https://github.com/Cog-Creators/Red-DiscordBot/graphs/contributors).\n\n"
                "This fork contains several modifications specific to Hibiki into core of Red. "
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
            value=f"<:py:821285406547902484> [`{python_version}`](https://www.python.org) • <:dpy:821284179086016553> [`{discord.__version__}`](https://github.com/Rapptz/discord.py) • <:red:821276871730790420> [`{version_info}`](https://pypi.org/project/Red-DiscordBot)",
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
                label="Support",
                url="https://izumibot.x10.mx/support",
                emoji=discord.PartialEmoji(
                    name="pat", animated=True, id="855023907383803945"
                ),
            )
        )
        await inter.reply(embed=embed, view=view)

    @dislash.guild_only()
    @info.sub_command(
        name="server", description="Get information about your server!"
    )
    async def slash_serverinfo(self, inter):
        guild = inter.guild
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
                shard_count=humanize_number(self.bot.shard_count),
            )
            if self.bot.shard_count > 1
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
            bot_name=inter.bot.user.name,
            bot_join=guild.me.joined_at.strftime("%d %b %Y %H:%M:%S"),
            since_join=humanize_number(
                (inter.message.created_at - guild.me.joined_at).days
            ),
        )

        data = discord.Embed(
            description=(
                f"{guild.description}\n\n" if guild.description else ""
            )
            + created_at,
            colour=await self.bot.embed_colour(),
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

        await inter.send(embed=data)

    @dislash.guild_only()
    @info.sub_command(
        name="user",
        options=[
            Option(
                "user",
                "The user you want to get info for",
                OptionType.USER,
                required=False,
            ),
        ],
        description="Get info about another use or yourself",
    )
    async def slash_userinfo(self, inter, *, user: discord.User = None):
        """Show information about a user.

        This includes fields for status, discord join date, server
        join date, voice state and previous names/nicknames.
        If the user has no roles, previous names or previous nicknames,
        these fields will be omitted.
        """
        user = user or inter.author
        guild = inter.guild

        # if inter.guild is None:
        #     inter.reply("Please run this in a guild and not my dms!")
        #     return

        roles = user.roles[-1:0:-1]
        names, nicks = await self.get_names_and_nicks(user)
        dt = user.joined_at
        dt1 = user.created_at
        unix_ts_utc = dt.replace(tzinfo=timezone.utc).timestamp()
        unix_ts_utc1 = dt1.replace(tzinfo=timezone.utc).timestamp()
        user_c_converter = int(unix_ts_utc1)
        user_j_converter = int(unix_ts_utc)

        since_created = "<t:{}:R>".format(user_c_converter)
        if user.joined_at is not None:
            since_joined = "<t:{}:R>".format(user_j_converter)
            user_joined = "<t:{}>".format(user_j_converter)
        else:
            since_joined = "?"
            user_joined = _("Unknown")
        user_created = "<t:{}>".format(user_c_converter)
        voice_state = user.voice
        member_number = (
            sorted(
                guild.members,
                key=lambda m: m.joined_at or inter.message.created_at,
            ).index(user)
            + 1
        )

        sharedguilds = (
            user.mutual_guilds
            if hasattr(user, "mutual_guilds")
            else {
                guild
                async for guild in AsyncIter(self.bot.guilds, steps=100)
                if user in guild.members
            }
        )

        created_on = _("{} - ({})\n").format(since_created, user_created)
        joined_on = _("{} - ({})\n").format(since_joined, user_joined)

        if user.is_on_mobile():
            statusemoji = (
                self.bot.get_emoji(STATUS_EMOJIS["mobile"])
                or "\N{MOBILE PHONE}"
            )
        elif any(
            a.type is discord.ActivityType.streaming for a in user.activities
        ):
            statusemoji = (
                self.bot.get_emoji(STATUS_EMOJIS["streaming"])
                or "\N{LARGE PURPLE CIRCLE}"
            )
        elif user.status.name == "online":
            statusemoji = (
                self.bot.get_emoji(STATUS_EMOJIS["online"])
                or "\N{LARGE GREEN CIRCLE}"
            )
        elif user.status.name == "offline":
            statusemoji = (
                self.bot.get_emoji(STATUS_EMOJIS["offline"])
                or "\N{MEDIUM WHITE CIRCLE}"
            )
        elif user.status.name == "dnd":
            statusemoji = (
                self.bot.get_emoji(STATUS_EMOJIS["dnd"])
                or "\N{LARGE RED CIRCLE}"
            )
        elif user.status.name == "idle":
            statusemoji = (
                self.bot.get_emoji(STATUS_EMOJIS["away"])
                or "\N{LARGE ORANGE CIRCLE}"
            )
        else:
            statusemoji = MISSING_EMOJI
        activity = _("**Chilling in {} status**").format(user.status)
        status_string = self.get_status_string(user)

        if roles:

            role_str = ", ".join([x.mention for x in roles])
            # 400 BAD REQUEST (error code: 50035): Invalid Form Body
            # In embed.fields.2.value: Must be 1024 or fewer in length.
            if len(role_str) > 1024:
                # Alternative string building time.
                # This is not the most optimal, but if you're hitting this, you are losing more time
                # to every single check running on users than the occasional user info invoke
                # We don't start by building this way, since the number of times we hit this should be
                # infintesimally small compared to when we don't across all uses of Red.
                continuation_string = _(
                    "and {numeric_number} more roles not displayed due to embed limits."
                )

                available_length = 1024 - len(
                    continuation_string
                )  # do not attempt to tweak, i18n

                role_chunks = []
                remaining_roles = 0

                for r in roles:
                    chunk = f"{r.mention}, "
                    chunk_size = len(chunk)

                    if chunk_size < available_length:
                        available_length -= chunk_size
                        role_chunks.append(chunk)
                    else:
                        remaining_roles += 1

                role_chunks.append(
                    continuation_string.format(numeric_number=remaining_roles)
                )

                role_str = "".join(role_chunks)

        else:
            role_str = None

        stoa = status_string or activity + "\n"
        l_sharedg = len(sharedguilds)

        data_r = await self.bot.http.request(
            RouteV9("GET", f"/users/{user.id}")
        )

        dg_id = data_r.get("id")
        dg_username = data_r.get("username")
        dg_discriminator = data_r.get("discriminator")

        if data_r.get("banner") != None:
            banner_hash = data_r.get("banner")
            animated = banner_hash.startswith("a_")
            extension = "gif" if animated else "png"
            banner_url = (
                "https://cdn.discordapp.com/banners/{}/{}.{}?size=4096".format(
                    user.id, banner_hash, extension
                )
            )

        else:
            banner_url = ""

        data = discord.Embed(colour=user.colour)

        if names:
            name_name = (
                _("**Previous Names:**")
                if len(names) > 1
                else _("**Previous Name:**")
            )
            name_val = filter_invites(", ".join(names))
            prev_names_val = "{}\n{}".format(
                name_name,
                name_val,
            )

        else:
            prev_names_val = ""

        data.set_image(url=banner_url)

        data.add_field(
            name=_("__User Info__"),
            value=_(
                "**Shared Servers:** {}\n" "**Joined Discord:** {}" "{}" "{}"
            ).format(
                l_sharedg,
                created_on,
                stoa,
                prev_names_val,
            ),
            inline=False,
        )

        if nicks:
            nick_name = (
                _("**Previous Nicknames:**")
                if len(nicks) > 1
                else _("**Previous Nickname:**")
            )
            nick_val = filter_invites(", ".join(nicks))
            prev_nicks_val = "{}\n{}\n".format(
                nick_name,
                nick_val,
            )

        else:
            prev_nicks_val = ""

        if role_str is not None:
            role_name = _("**Roles:**") if len(roles) > 1 else _("**Role:**")
            role_val = role_str
            prev_rol_val = "{}\n{}\n".format(
                role_name,
                role_val,
            )

        else:
            prev_rol_val = "This person doesn't seem to have any roles."

        if voice_state and voice_state.channel:
            voice_name = _("Current voice channel:")
            voice_val = "{0.mention} ID: {0.id}".format(voice_state.channel)
            prev_voice_val = "{} {}".format(
                voice_name,
                voice_val,
            )

        else:
            prev_voice_val = ""

        data.add_field(
            name=_("__Member info__"),
            value=_("**Joined this server:** {}" "{}" "{}" "{}").format(
                joined_on,
                prev_nicks_val,
                prev_rol_val,
                prev_voice_val,
            ),
            inline=False,
        )

        name = str(user)
        name = " ~ ".join((name, user.nick)) if user.nick else name
        name = discord.utils.escape_markdown(
            filter_invites(name), as_needed=True
        )
        avatar = user.avatar.url
        guild_badges = []
        badges = []
        flags = [f.name for f in user.public_flags.all()]
        if guild.owner == user:
            guild_badges.append(
                str(self.bot.get_emoji(EMOJIS.get("owner"))) or MISSING_EMOJI
            )
        if user.premium_since:
            guild_badges.append(
                str(self.bot.get_emoji(EMOJIS.get("booster"))) or MISSING_EMOJI
            )
        if user.bot and "verified_bot" not in flags:
            badges.append(
                str(self.bot.get_emoji(EMOJIS.get("bot"))) or MISSING_EMOJI
            )
        for badge in sorted(flags):
            if badge == "verified_bot":
                badges.append(str(self.bot.get_emoji(EMOJIS["verified_bot"])))
                badges.append(str(self.bot.get_emoji(EMOJIS["verified_bot2"])))
                continue
            badges.append(
                str(self.bot.get_emoji(EMOJIS.get(badge)) or MISSING_EMOJI)
            )
        data.title = (
            f"{statusemoji} {name} {''.join(guild_badges)} {''.join(badges)}"
        )
        if len(data.title) > 256:
            data.title = f"{statusemoji} {name} {''.join(guild_badges)}"
            data.description = "".join(badges) + "\n" + data.description
        data.set_thumbnail(url=avatar)

        if not user.bot:
            special_badges = []
            for guild_id, roles in SPECIAL_BADGES.items():
                if (guild := self.bot.get_guild(guild_id)) and (
                    special_member := guild.get_member(user.id)
                ):
                    for r in reversed(special_member.roles):
                        if r.id in roles:
                            special_badges.append(
                                f"{self.bot.get_emoji(roles[r.id])} {r.name}"
                            )
            if special_badges:
                data.add_field(
                    name="Special Badges:", value="\n".join(special_badges)
                )
        member_number = (
            sorted(
                inter.guild.members,
                key=lambda m: m.joined_at or inter.message.created_at,
            ).index(user)
            + 1
        )
        data.set_footer(
            text="Member: #{} • User Id: {}".format(
                member_number,
                dg_id,
            )
        )
        await inter.reply(embed=data)
