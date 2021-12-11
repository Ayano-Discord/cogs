# Future Imports
from __future__ import annotations

# Standard Library Imports
from datetime import datetime as dt

# Dependency Imports
from redbot.core import commands, Config
import discord


class on_connect(commands.Cog):
    """Owner only commands to manage shard events"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=0xA203A2A, force_registration=True
        )
        default_global = {
            "event_channel": None,
            "type": 0,
        }
        self.config.register_global(**default_global)
        self.type = None
        self.webhook = None

    async def webhook_check(
        self, webhook: discord.Webhook
    ) -> bool:  # from https://github.com/phenom4n4n/phen-cogs/blob/4085e5098cebf4643963064c25c9b1e52bfe2f7f/webhook/webhook.py#L428
        return webhook.token

    async def build_cache(self):
        """
        Smth Smth
        """
        self.type = await self.config.type()
        if (
            await self.config.type() == 0
            and await self.config.event_channel() != None
        ):
            channel = await self.chan_get_or_fetch(
                int(await self.config.event_channel())
            )
            chan_hooks = await channel.webhooks()
            webhook_list = [
                w for w in chan_hooks if await self.webhook_check(w)
            ]
            if webhook_list:
                webhook = webhook_list[0]
                self.webhook = webhook
        else:
            if await self.config.event_channel() is not None:
                self.channel = int(await self.config.event_channel())

    async def chan_get_or_fetch(
        self, channel_id: int
    ):  # Just a edited version of redbot.core.bot get_or_fetch_user
        """
        Get or fetch a channel.
        """
        if (channel := self.bot.get_channel(channel_id)) is not None:
            return channel
        return await self.bot.fetch_channel(channel_id)

    async def send_event(self, embed: discord.Embed):
        """
        Send events.
        """
        if self.type is None:
            self.type = await self.config.type()
        if self.type == 0 and self.webhook != None:
            await self.webhook.send(
                embed=embed,
                username=self.bot.user.name,
                avatar=ctxavatar.with_static_format("png").url,
            )
        else:
            if self.type == 1 and self.channel:
                channel = await self.chan_get_or_fetch(self.channel)
                if channel:
                    await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_connect(self):
        """Sends a message when the bot connects to discord."""
        embed = discord.Embed(
            title="Connected to discord.",
            description="I've successfully established a connection to discord.",
            color=0x81E0A9,
            timestamp=dt.utcnow(),
        )
        embed.set_thumbnail(
            url=self.bot.user.avatar.with_static_format("png").url
        )
        await self.send_event(embed)

    @commands.Cog.listener()
    async def on_shard_connect(self, shard_id: int):
        """
        Sends a message when any shard ID is connected.
        """
        embed = discord.Embed(
            color=0x81E0A9,
            title=f"{self.bot.user.name} - Shard Connect",
            timestamp=dt.utcnow(),
        )
        embed.description = f"\N{BALLOT BOX WITH CHECK}\N{VARIATION SELECTOR-16} Shard `{shard_id}` is now connected."
        await self.send_event(embed)

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id: int):
        """
        Sends a message when any shard ID becomes ready.
        """
        embed = discord.Embed(
            color=0x81E0A9,
            title=f"{self.bot.user.name} - Shard Ready",
            timestamp=dt.utcnow(),
        )
        embed.description = (
            f"\N{LARGE GREEN CIRCLE} Shard `{shard_id}` is now ready."
        )
        await self.send_event(embed)

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Sends a message when the bot becomes ready.
        """
        embed = discord.Embed(
            color=0x81E0A9,
            description=f"<@762976674659696660> is back online  :white_check_mark:",
            timestamp=dt.utcnow(),
        )
        await self.send_event(embed)

    @commands.Cog.listener()
    async def on_shard_disconnect(self, shard_id: int):
        """
        Sends a message when the shard ID is disconnected.
        """
        embed = discord.Embed(
            color=0xE74C3C,
            description=f"\N{NO ENTRY}\N{VARIATION SELECTOR-16} Shard `{shard_id}` has disconnected.",
            timestamp=dt.utcnow(),
        )
        await self.send_event(embed)

    @commands.Cog.listener()
    async def on_disconnect(self):
        """
        Sends a message when the bot is disconnected.
        """
        embed = discord.Embed(
            color=0xE74C3C,
            title=f"{self.bot.user.name} - Disconnect",
            timestamp=dt.utcnow(),
        )
        embed.description = f"\N{NO ENTRY}\N{VARIATION SELECTOR-16} Bot disconnected in shard(s) `{self.bot.shard_ids or [0]}`."
        await self.send_event(embed)

    @commands.Cog.listener()
    async def on_shard_resumed(self, shard_id: int):
        """
        Sends a message when the shard ID is resumed.
        """
        embed = discord.Embed(
            color=0x81E0A9,
            description=f"Shard ID `{shard_id}` reconnected to Gateway. <:idle:749221433095356417>",
            timestamp=dt.utcnow(),
        )
        await self.send_event(embed)

    @commands.Cog.listener()
    async def on_resumed(self):
        """
        Sends a message when the bot is resumed.
        """
        embed = discord.Embed(
            color=0x81E0A9,
            title=f"{self.bot.user.name} - Resumed",
            timestamp=dt.utcnow(),
        )
        embed.description = f"\N{BALLOT BOX WITH CHECK}\N{VARIATION SELECTOR-16} Bot resumed on shard(s) `{self.bot.shard_ids or [0]}`."
        await self.send_event(embed)

    @commands.command(name="oct")
    @commands.is_owner()
    async def on_connect_test(self, ctx):
        """Just a event sender test"""
        if not await self.config.event_channel():
            return await ctx.send(
                f"Setup a channel first using `{ctx.clean_prefix}connectset channel`."
            )
        embed = discord.Embed(
            color=await ctx.embed_color(),
            title="Hook Test",
            timestamp=dt.utcnow(),
        )
        await self.send_event(embed)
        await ctx.tick()

    @commands.group()
    @commands.is_owner()
    async def connectset(self, ctx: commands.Context):
        """
        Setting up the connection thingy
        """

    @connectset.command()
    async def channel(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """
        Setup the channel where the events will be sent.
        """
        if channel is None:
            await self.config.event_channel.set(None)
            return await ctx.send(
                "Event channel has been removed. Set a new one using the same command."
            )
        await self.config.event_channel.set(channel.id)
        await self.build_cache()
        await ctx.send(f"Event channel has been set to: {channel.mention}")

    @connectset.command()
    async def type(self, ctx: commands.Context, type: int):
        """
        Set the type of the event.
        If you want it to use webhooks put 0 as the type but keep in mind bot needs webhook perms for that, otherwise 1 for normal messages.
        Default is o.
        """
        if await self.config.event_channel() is None:
            return await ctx.send(
                f"You need to set the channel first. You can do so by doing {ctx.clean_prefix}connectset channel"
            )
        if type == 0:
            channel = self.bot.get_channel(
                int(await self.config.event_channel())
            )
            if not channel.permissions_for(channel.guild.me).manage_webhooks:
                return await ctx.send(
                    "I need the `manage_webhooks` permission to use webhooks."
                )
            await self.config.type.set(type)
            await channel.create_webhook(
                name=f"{self.bot.user.name}",
                reason="Shard event poster",
                avatar=await self.bot.user.avatar.with_static_format(
                    "png"
                ).url.read(),
            )
            await ctx.send("Webhooks are now being used.")
            await self.build_cache()
        elif type == 1:
            await self.config.type.set(type)
            await ctx.send("Normal messages are now being used.")
            await self.build_cache()
        else:
            await ctx.send(
                "Invalid type. Choose between 0 (webhook) or 1 (normal messages)."
            )

    @connectset.command(aliases=["settings"])
    async def showsettings(self, ctx: commands.Context):
        """
        Show the current settings.
        """
        await ctx.send(
            "**__On Connect Settings__**\n"
            f"```nim\nEvent Channel: {self.channel}\n"
            f"Type: {'Webhook Messages' if self.type == 0 else 'Normal Messages'}```"
        )
