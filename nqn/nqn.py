# Future Imports
from __future__ import annotations

# Standard Library Imports
from typing import Optional, Union
import asyncio
import logging
import re
import sys

# Dependency Imports
from discord.ext import tasks
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.i18n import cog_i18n, Translator
from redbot.core.utils.chat_formatting import humanize_list as listt
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate
import discord

EMOJI_RE = re.compile(r"\B:([a-zA-Z0-9\_]+):\B")
log = logging.getLogger("red.mine.nqn")
_ = Translator("NotQuiteNitro", __file__)


@cog_i18n(_)
class NotQuiteNitro(commands.Cog):
    """Use animated and custom emojis without discord nitro."""

    __version__ = "0.3.5"

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config: Config = Config.get_conf(
            self, identifier=462364255128256513, force_registration=True
        )

        default_guild = {
            "toggle": False,
            "ignored_channels": [],
            "ignored_users": [],
        }

        self.config.register_guild(**default_guild)

        self.re_cache.start()

    def cog_unload(self) -> None:
        self.re_cache.cancel()

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Sinbad!"""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def red_get_data_for_user(self, *, user_id: int) -> dict:
        """This cog does not story any end user data."""
        return {}

    async def red_delete_data_for_user(self, **kwargs) -> None:
        """Nothing to delete."""
        return

    @tasks.loop(seconds=60)
    async def re_cache(self) -> None:
        """Update the cache every 60 seconds with the config."""
        self.config_cache: dict = await self.config.all_guilds()

    @re_cache.before_loop
    async def before_re_cache(self) -> None:
        """Wait for red to startup properly."""
        await self.bot.wait_until_red_ready()

    @commands.group(name="nqnset")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def _nqn_set(self, ctx: commands.Context):
        """Base command to manage NotQuiteNitro settings."""

    @_nqn_set.command(name="toggle")
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def _toggle(self, ctx: commands.Context):
        """Toggle animated emojis in this server."""
        config: bool = await self.config.guild(ctx.guild).toggle()
        if not config:
            await self.config.guild(ctx.guild).toggle.set(True)
            await ctx.reply(_("NQN is now enabled in this server."))
            return

        await self.config.guild(ctx.guild).toggle.set(False)
        await ctx.reply(_("NQN is now disabled in this server."))

    @_nqn_set.command(name="ignorechannel", aliases=["ignorechan"])
    async def _ignore_channel(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel] = None,
    ):
        """Add a channel to the list of channels to ignore NQN.

        **Examples**
        - `[p]nqnset ignorechannel #testing`
        This will add #testing to the list of ignored channels.

        - `[p]nqnset ignorechannel 133251234164375552`
        This will add #testing to the list of ignored channels.

        **Arguments**
        - `[channel]` - The channel to ignore. Leave empty to set as the current channel.
        """
        if not channel:
            channel = ctx.channel

        config: list = await self.config.guild(ctx.guild).ignored_channels()
        if channel.id not in config:
            config.append(channel.id)
            await self.config.guild(ctx.guild).ignored_channels.set(config)
            await ctx.reply(
                _("{c} is now ignored by NQN").format(c=channel.mention)
            )
            return

        await ctx.reply(
            _("{c} is already ignored by NQN!").format(c=channel.mention)
        )

    @_nqn_set.command(name="unignorechannel", aliases=["unignorechan"])
    async def _unignore_channel(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel] = None,
    ):
        """Remove a channel from the list of channels to ignore NQN.

        **Examples**
        - `[p]nqnset unignorechannel #testing`
        This will remove #testing from the list of ignored channels.

        - `[p]nqnset unignorechannel 133251234164375552`
        This will remove #testing from the list of ignored channels.

        **Arguments**
        - `[channel]` - The channel to unignore. Leave empty to set as the current channel.
        """
        if not channel:
            channel = ctx.channel

        config: list = await self.config.guild(ctx.guild).ignored_channels()
        if channel.id in config:
            config.remove(channel.id)
            await self.config.guild(ctx.guild).ignored_channels.set(config)
            await ctx.reply(
                _("{c} is not ignored by NQN now").format(c=channel.mention)
            )
            return

        await ctx.reply(
            _("{c} is not ignored by NQN!").format(c=channel.mention)
        )

    @_nqn_set.command(name="ignoreuser")
    async def _ignore_user(self, ctx: commands.Context, user: discord.Member):
        """Add a user to the list of users to get ignored by NQN.

        **Examples**
        - `[p]nqnset ignoreuser @GhOsT`
        This will add GhOsT to the list of ignored users.

        - `[p]nqnset ignoreuser 722168161713127435`
        This will add GhOsT to the list of ignored users.

        **Arguments**
        - `<user>` - The user to ignore. You can mention them or give their id.
        """
        config: list = await self.config.guild(ctx.guild).ignored_users()
        if user.id not in config:
            config.append(user.id)
            await self.config.guild(ctx.guild).ignored_users.set(config)
            await ctx.reply(_("{u} is now ignored by NQN").format(u=user))
            return

        await ctx.reply(_("{u} is already ignored by NQN!").format(u=user))

    @_nqn_set.command(name="unignoreuser")
    async def _unignore_user(
        self, ctx: commands.Context, user: discord.Member
    ):
        """Remove a user from the list of users to get ignored by NQN.

        **Examples**
        - `[p]nqnset unignoreuser @GhOsT`
        This will remove GhOsT from the list of ignored users.

        - `[p]nqnset unignoreuser 722168161713127435`
        This will remove GhOsT from the list of ignored users.

        **Arguments**
        - `<user>` - The user to unignore. You can mention them or give their id.
        """
        config: list = await self.config.guild(ctx.guild).ignored_users()
        if user.id in config:
            config.remove(user.id)
            await self.config.guild(ctx.guild).ignored_users.set(config)
            await ctx.reply(_("{u} is not ignored by NQN now").format(u=user))
            return

        await ctx.reply(_("{u} is not ignored by NQN!").format(u=user))

    @_nqn_set.command(name="clearsettings", aliases=["clear"])
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def _clear_settings(self, ctx: commands.Context):
        """Clear all the NQN settings for this server."""
        config = await self.config.guild(ctx.guild).all()
        if not config:
            await ctx.reply(_("There is nothing to clear in the settings!"))
            return

        message = await ctx.reply(
            _("Do you want to clear the NQN settings for this server?")
        )

        start_adding_reactions(message, ReactionPredicate.YES_OR_NO_EMOJIS)

        try:
            pred = ReactionPredicate.yes_or_no(message, ctx.author)
            await ctx.bot.wait_for("reaction_add", check=pred, timeout=45)
            if pred.result is True:
                await self.config.guild(ctx.guild).clear_raw()
                await message.edit(
                    content=_("Successfully cleared the settings!")
                )
                return

            await message.edit(
                content=_("Okay, not clearing the settings today...")
            )
        except asyncio.TimeoutError:
            await message.edit(content=_("Timed out, try again later..."))

    @_nqn_set.command(name="showsettings", aliases=["settings"])
    async def _show_settings(self, ctx: commands.Context):
        """Shows the NQN settings for this server."""
        config: dict = await self.config.guild(ctx.guild).all()
        toggle: bool = config.get("toggle")
        ignored_chan_ids: list = config.get("ignored_channels")
        ignored_user_ids: list = config.get("ignored_users")
        ignored_chan = [
            c.mention for c in ctx.guild.channels if c.id in ignored_chan_ids
        ]
        ignored_user = [
            u.mention for u in ctx.guild.members if u.id in ignored_user_ids
        ]
        toggled_str = _("Yes.") if toggle else _("No.")
        ignored_chan_str = listt(ignored_chan) if ignored_chan else _("None.")
        ignored_user_str = listt(ignored_user) if ignored_user else _("None.")
        embed = (
            discord.Embed(
                title=_("NQN Settings"),
                description="**Enabled:** {}".format(toggled_str),
                colour=await ctx.embed_colour(),
            )
            .add_field(
                name="Ignored Channels:",
                value=ignored_chan_str,
                inline=True if len(ignored_chan) > 1 else False,
            )
            .add_field(
                name="Ignored Users:",
                value=ignored_user_str,
                inline=True if len(ignored_user) > 1 else False,
            )
        )
        await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if not message.guild or message.author.bot or not message.content:
            return

        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return
        try:
            cache = self.config_cache[message.guild.id]
        except KeyError:
            return  # handle keyerror or logs go brrrrr

        guild: discord.Guild = message.guild
        channel: discord.TextChannel = message.channel
        author: discord.Member = message.author

        if any(
            [
                self.config_cache[guild.id]["toggle"] is False,
                channel.id in self.config_cache[guild.id]["ignored_channels"],
                author.id in self.config_cache[guild.id]["ignored_users"],
            ]
        ):
            return

        def content_to_emoji(content: re.Match) -> Union[str, None]:
            emoji_name = content.group(1)
            emoji: discord.Emoji = discord.utils.get(
                guild.emojis, name=emoji_name, available=True
            ) or discord.utils.get(
                self.bot.emojis, name=emoji_name, available=True
            )
            if not emoji:
                return

            return str(emoji)

        if not re.search(EMOJI_RE, message.content):
            return

        newcontent = re.sub(EMOJI_RE, content_to_emoji, message.content)
        if not newcontent:
            return

        webhooks = await channel.webhooks()
        if not webhooks:
            webhook = await channel.create_webhook(name="NotQuiteNitro")
        else:
            usable_webhooks = [hook for hook in webhooks if hook.token]
            if not usable_webhooks:
                webhook = await channel.create_webhook(name="NotQuiteNitro")
            else:
                webhook = usable_webhooks[0]

        try:
            await message.delete()
            await webhook.send(
                content=newcontent,
                username=author.display_name,
                avatar_url=author.avatar.url,
            )
        except discord.HTTPException as e:
            log.error("An error occured: {e}", exc_info=sys.exc_info())
            return
