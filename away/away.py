# Future Imports
from __future__ import annotations

# Dependency Imports
from redbot.core import commands, Config
from redbot.core.utils import AsyncIter
import discord


class Away(commands.Cog):
    """Toggle your away status!"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=809033759898075147, force_registration=True
        )
        default_user = {
            "away_message": None,
            "default_msg": "{} is away, try contacting them again later.",
            "user_id": None,
        }
        self.config.register_user(**default_user)
        self.away_users = []

    async def monkey_send(
        self, message: discord.Message, embed: discord.Embed
    ):
        try:
            await message.reply(embed=embed, mention_author=False)
        except (discord.Forbidden, discord.HTTPException):
            await message.channel.send(embed=embed)

    @commands.guild_only()
    @commands.command(name="away")
    async def cmd_away(self, ctx: commands.Context, message: str = None):
        em = discord.Embed(title="You're now away.")
        if message:
            if len(message) < 2:
                await self.monkey_send(
                    "Your message needs to be longer than 1 character!"
                )
                return
            else:
                em.add_field(
                    name="Your message has been set to;", value=message
                )
                # await self.config.user(ctx.author).user_id.set(message)

        sharedguilds = (
            ctx.author.mutual_guilds
            if hasattr(ctx.author, "mutual_guilds")
            else {
                guild
                async for guild in AsyncIter(self.bot.guilds, steps=100)
                if ctx.author in guild.members
            }
        )
        if len(sharedguilds) < 2:
            footer_text = "NOTE: Sending a message in this server will result in you being removed from your afk status"
        else:
            footer_text = (
                "NOTE: Sending a message in any of the {} servers I share with you, will result in you being removed from your AFK status"
            ).format(len(sharedguilds))
        em.set_footer(text=footer_text)
        await ctx.send(embed=em)
        self.away_users.append(ctx.author.id)
        if message is None:
            await self.config.user(ctx.author).away_message.set(
                f"{ctx.author.name} is currently away, pleae try contacting them again later."
            )

    @commands.group(name="awayset")
    @commands.guild_only()
    async def cmd_awayset(self, ctx: commands.Context):
        """
        Settings for away
        """
        pass

    @cmd_awayset.command(name="setdefault", aliases=["setdef"])
    async def cmd_away_default_msg(
        self, ctx: commands.Context, message: str = None
    ):
        """
        Set your default message, this message will be used if you don't specify a message when running `%away`
        """
        if not message:
            await self.config.user(ctx.author).default_msg.set(
                "{} is away, try contacting them again later."
            )
            await ctx.send("Your default message has been reset.")
            return
        if len(message) < 5:
            await ctx.send(
                "Your default message has to be longer than 5 characters."
            )
        await ctx.send(
            "Your default message has been set to `{}`.".fornat(message)
        )
        await self.config.user(ctx.author).default_msg.set(message)

    @commands.Cog.listener()
    async def on_message(
        self, message: discord.Message
    ):  # This is a listener, it will run every time a message is sent in a server
        if not message.guild:
            return
        if message.author.id not in self.away_users:
            return
        await message.channel.send("You are now back!")
        self.away_users.pop(self.away_users.index(message.author.id))

    @commands.Cog.listener("on_message")
    async def mention_listener(
        self,
        message,
        #         channel: discord.TextChannel
    ):
        # print("got this far")
        guild = message.guild
        if not guild:
            return
        # if not message.guild:
        #     return
        # print("got this far 1")
        if not message.mentions or message.author.bot:
            return
        if not message.channel.permissions_for(guild.me).send_messages:
            return
        #  print("got this far 2")
        for member in message.mentions:
            if member.id in self.away_users:
                away_msg = await self.config.user(member).away_message()
                embed = discord.Embed(
                    title=f"{member.name}  is currently away.",
                    description=f"{away_msg}",
                )
                await message.channel.send(embed=embed)
        # for author in message.mentions:
        #     await message.channel.send("You are now back!")

    @commands.Cog.listener("on_message")
    async def mention_listener_2(
        self,
        message,
        #         channel: discord.TextChannel
    ):
        print("got this far")
        guild = message.guild
        if not guild:
            return
        # if not message.guild:
        #     return
        print("got this far 1")
        if not message.mentions or message.author.bot:
            return
        if not message.channel.permissions_for(guild.me).send_messages:
            return
        print("got this far 2")
        for mentions in message.mentions:
            if mentions.id in self.away_users:
                away_msg = await self.config.user(mentions).away_message()
                embed = discord.Embed(
                    title=f"{mentions.name}  is currently away.",
                    description=f"{away_msg}",
                )
                await self.monkey_send(embed=embed)
        # for author in message.mentions:
        #     await message.channel.send("You are now back!")


def setup(bot):
    cog = Away(bot)
    bot.add_cog(cog)
