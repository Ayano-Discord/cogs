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
from redbot.core.utils.chat_formatting import humanize_number
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
        # if inter.guild is None:
        #     inter.reply("Please run this in a guild and not my dms!")
        #     return
        "Get current server info."
        guild = inter.guild
        levels = {
            "None - No criteria set.": discord.VerificationLevel.none,
            "Low - Member must have a verified email on their Discord account.": discord.VerificationLevel.low,
            "Medium - Member must have a verified email and be registered on Discord for more than five minutes.": discord.VerificationLevel.medium,
            "High - Member must have a verified email, be registered on Discord for more than five minutes, and be a member of the guild itself for more than ten minutes.": discord.VerificationLevel.high,
            "Extreme - Member must have a verified phone on their Discord account.": discord.VerificationLevel.highest,
        }
        filters = {
            "Disabled - The guild does not have the content filter enabled.": discord.ContentFilter.disabled,
            "No Role - The guild has the content filter enabled for members without a role.": discord.ContentFilter.no_role,
            "All Members - The guild has the content filter enabled for every member.": discord.ContentFilter.all_members,
        }
        regions = {
            "US West": discord.VoiceRegion.us_west,
            "US East": discord.VoiceRegion.us_east,
            "US South": discord.VoiceRegion.us_south,
            "US Central": discord.VoiceRegion.us_central,
            "London": discord.VoiceRegion.london,
            "Sydney": discord.VoiceRegion.sydney,
            "Amsterdam": discord.VoiceRegion.amsterdam,
            "Frankfurt": discord.VoiceRegion.frankfurt,
            "Brazil": discord.VoiceRegion.brazil,
            "Hong Kong": discord.VoiceRegion.hongkong,
            "Russia": discord.VoiceRegion.russia,
            "VIP US East": discord.VoiceRegion.vip_us_east,
            "VIP US West": discord.VoiceRegion.vip_us_west,
            "VIP Amsterdam": discord.VoiceRegion.vip_amsterdam,
            "Singapore": discord.VoiceRegion.singapore,
            "EU Central": discord.VoiceRegion.eu_central,
            "EU West": discord.VoiceRegion.eu_west,
        }
        verif_lvl = "None"
        for text, dvl in levels.items():
            if dvl is guild.verification_level:
                verif_lvl = text
        for response, filt in filters.items():
            if filt is guild.explicit_content_filter:
                content_fiter = response
        feats = ""
        if guild.features != []:
            for feature in guild.features:
                feats += feature + "\n"
        else:
            feats = "None"
        if guild.emojis:
            emotes_list = ", ".join(
                [
                    f"`{emoji.name}` - <:{emoji.name}:{emoji.id}>"
                    for emoji in guild.emojis[0:10]
                ]
            )
        else:
            emotes_list = "None"
        if len(guild.roles) > 1:
            roles_list = ", ".join(
                [
                    f"`{role}`"
                    for role in guild.roles[::-1]
                    if role.name != "@everyone"
                ]
            )
        else:
            roles_list = "None"
        server_region = "N/A"
        for name, reg in regions.items():
            if reg is guild.region:
                server_region = name
        embed = discord.Embed(title="Server info", color=guild.me.color)
        embed.set_author(name=f"{guild.name} - {guild.id}")
        embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Owner", value=guild.owner)
        embed.add_field(name="Owner ID", value=guild.owner.id)
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Text Channels", value=len(guild.text_channels))
        embed.add_field(name="Voice Channels", value=len(guild.voice_channels))
        embed.add_field(
            name="Created at",
            value=guild.created_at.strftime("%d.%m.%Y %H:%M"),
        )
        embed.add_field(name="Categories", value=len(guild.categories))
        embed.add_field(name="Region", value=server_region)
        embed.add_field(name=f"Roles ({len(guild.roles)})", value=roles_list)
        embed.add_field(name=f"Features ({len(guild.features)})", value=feats)
        embed.add_field(name="Verification Level", value=verif_lvl)
        embed.add_field(name="Content Filter", value=content_fiter)
        embed.add_field(
            name=f"Emojis ({len(guild.emojis)})", value=emotes_list
        )
        await inter.reply(embed=embed)

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
