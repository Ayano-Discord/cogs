# Future Imports
from __future__ import annotations

# Standard Library Imports
from logging import basicConfig, DEBUG
import logging
import random

# Dependency Imports
from discord.ext import tasks
from discord.ui import View
from dislash import *

# from redbot.core import bot
from dislash.interactions import ActionRow, Button, ButtonStyle
from dislash.interactions.application_command import *
from redbot.core import commands

# from redbot.core.i18n import cog_i18n, Translator
from redbot.core.utils.chat_formatting import humanize_list, humanize_number
import discord
import dislash

log = logging.getLogger("red.mine.slashcmd")
test_guilds = [852094131047104593]

# _ = Translator("slash", __file__)


# @cog_i18n(_)
class Slashcmd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.change_presence.start()

    def cog_unload(self):
        self.change_presence.cancel()

    @slash_command(description="Vote for Izumi and earn rewards!")
    async def vote(self, inter):
        """Vote For Izumi And Earn Rewards"""
        my_buttons = [
            ActionRow(
                Button(
                    style=ButtonStyle.link,
                    label="Top.gg - Upvote",
                    emoji=discord.PartialEmoji(
                        name="dbl", animated=False, id="868770213796147270"
                    ),
                    url="https://top.gg/bot/762976674659696660/vote",
                ),
                Button(
                    style=ButtonStyle.link,
                    label="BFD - Upvote",
                    emoji=discord.PartialEmoji(
                        name="bfdspin", animated=True, id="868769753664208926"
                    ),
                    url="https://discords.com/bots/bot/762976674659696660/vote",
                ),
            )
        ]
        embed = discord.Embed(colour=0x2F3136)
        embed.set_thumbnail(
            url=self.bot.user.avatar.with_static_format("png").url
        )
        embed.add_field(
            name="Here are the bot lists where you can upvote me!",
            value=(
                "[Top.gg](https://top.gg/bot/762976674659696660/vote) • "
                "[Discord Extreme list (DELLY)](https://discordextremelist.xyz/en-US/bots/762976674659696660) • "
                "[Discord Boats](https://discord.boats/bot/762976674659696660/vote) • "
                "[BFD](https://discords.com/bots/bot/762976674659696660/vote) • "
                "[Fateslist](https://fateslist.xyz/bot/762976674659696660) • "
                "[DBL](https://discordbotlist.com/bots/izumi-8159/upvote) • "
                "[Void](https://voidbots.net/bot/762976674659696660/vote)"
            ),
            inline=True,
        )
        embed.set_footer(
            text=(
                "Only Top.gg will give you currency rewards, "
                "but any vote is appreciated. ❤️"
            )
        )
        await inter.reply(embed=embed, components=my_buttons)

    @slash_command(
        description="Invite to the support server or the invite for Izumi!",
        options=[
            Option(
                "invite",
                "Choose if you want the invite to my support server or an invite to invite me.",
                choices=[
                    OptionChoice("Bot", "bot"),
                    OptionChoice("Support", "sup"),
                ],
                required=True,
            )
            # By default, Option is optional
            # Pass required=True to make it a required arg
        ],
    )
    async def invite(self, inter, invite):

        embed = discord.Embed(title="Thanks for using me!", colour=0x2F3136)
        embed.set_thumbnail(
            url=self.bot.user.avatar.with_static_format("png").url
        )

        if invite == "sup":
            embed.add_field(
                name="Support server",
                value=(
                    "Join [izumi Support](https://izumibot.x10.mx/support) if you need support, have any suggestions, or just want to vibe with us!"
                ),
                inline=False,
            )

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

        else:
            embed.add_field(
                name="Bot Invite",
                value=("[Click Here!](https://izumibot.x10.mx/invite)"),
                inline=False,
            )

            my_buttons = [
                ActionRow(
                    Button(
                        style=ButtonStyle.link,
                        label="Invite",
                        emoji=discord.PartialEmoji(
                            name="love",
                            animated=False,
                            id="820231241768108044",
                        ),
                        url="https://izumibot.x10.mx/invite",
                    )
                )
            ]

        await inter.reply(embed=embed, components=my_buttons)

    @slash_command(
        description=(
            "Forgot Izumi's prefix? Run this command to see all the prefixes Izumi has on this server!"
        )
    )
    async def prefix(self, inter):

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

        if inter.guild is None:
            embed = discord.Embed(title="My prefixes are:", colour=0x2F3136)
            embed.set_thumbnail(
                url=self.bot.user.avatar.with_static_format("png").url
            )
            embed.add_field(
                name="\u200b",
                value=(
                    """ **Hey there!** <a:cappie_excited:818343422921408523>
            My global prefixes are <@762976674659696660>, `%`, `I`, `izumi `
            You can type to `%help` view all of my commands!
            Need some help? Join my [support server!](https://izumibot.x10.mx/support)"""
                ),
                inline=False,
            )
        else:
            prefixes = await self.bot.get_prefix(inter.channel)
            prefixes.remove(f"<@!{self.bot.user.id}> ")
            sorted_prefixes = sorted(prefixes, key=len)
            if len(sorted_prefixes) > 500:
                return
            embed = discord.Embed(title="My prefixes are:", colour=0x2F3136)
            embed.set_thumbnail(
                url=self.bot.user.avatar.with_static_format("png").url
            )
            embed.add_field(
                name="\u200b",
                value=(
                    f"""**Hey there!** <a:cappie_excited:818343422921408523>
            My prefixes in this server are {humanize_list(prefixes)}
            You can type `{sorted_prefixes[0]}help` to view all of my commands!
            Need some help? Join my [support server!](https://izumibot.x10.mx/support)"""
                ),
                inline=False,
            )
        await inter.create_response(embed=embed, components=my_buttons)

    @tasks.loop(seconds=360)
    async def change_presence(self):

        # status_picker = "stats", "watching", "playing", "streaming"

        # statuses = random.choice(status_picker)

        # playing_statuses = (
        #     "With Your Heart",
        #     "Genshin And Honkai Impact",
        #     "While Losing Sleep",
        #     "With the Onii-chan",
        #     "With My Master",
        # )

        # watching_statuses = (
        #     "Demon Slayer The Movie: Mugen Train",
        #     "Your Name",
        #     "A Whisper Away",
        #     "A Silent Voice",
        #     "Summer Wars",
        # )

        # stream_urls = (
        #     "https://twitch.tv/thean1meman/",
        #     "https://twitch.tv/discord/",
        #     "https://izumibot.x10.mx/invite/",
        #     "https://izumibot.x10.mx/support/",
        #     "https://www.twitch.tv/directory/game/Genshin%20Impact",
        # )

        # bot_guilds_l = len(self.bot.guilds)
        # visible_users = sum(len(s.members) for s in self.bot.guilds)
        # visible_users_1 = humanize_number(visible_users)

        # if statuses == "watching":
        #     my_statuses = random.choice(watching_statuses)
        #     status_type = discord.ActivityType.watching
        #     activity_chooser = discord.Activity(
        #         type=status_type,
        #         name=my_statuses,
        #         status=discord.Status.online,
        #     )

        # if statuses == "playing":
        #     my_statuses = random.choice(playing_statuses)
        #     status_type = discord.ActivityType.playing
        #     activity_chooser = discord.Activity(
        #         type=status_type,
        #         name=my_statuses,
        #         status=discord.Status.dnd,
        #     )

        # if statuses == "streaming":
        #     my_statuses = random.choice(watching_statuses)
        #     url = random.choice(stream_urls)
        #     activity_chooser = discord.Streaming(
        #         name=my_statuses,
        #         url=url,
        #     )

        # else:
        #     my_statuses = (
        #         "@Hibiki help or %help | {} servers and {} users!"
        #     ).format(
        #         bot_guilds_l,
        #         visible_users_1,
        #     )
        #     status_type = discord.ActivityType.listening
        #     activity_chooser = discord.Activity(
        #         type=status_type,
        #         name=my_statuses,
        #         status=discord.Status.online,
        #     )

        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="{} Servers! | %help".format(len(self.bot.guilds)),
                status=discord.Status.online,
            )
        )

    @change_presence.before_loop
    async def before_change_presenc(self):
        await self.bot.wait_until_red_ready()

    #     @commands.Cog.listener()
    #     async def on_slash_command_error(self, inter, error):
    # #        print(f"Traceback:\n{__import__('traceback').format_exc()}")
    # #        print(error)
    #         guild = self.bot.get_guild(852094131047104593)
    #         channel = guild.get_channel(852094131651870759)
    #         await channel.send(
    #             f"Traceback:\n{__import__('traceback').format_exc()}\n{error}"
    #         )
    #         view = View()
    #         view.add_item(
    #             discord.ui.Button(
    #                 label="Support",
    #                 url="https://izumibot.x10.mx/support",
    #                 emoji=discord.PartialEmoji(
    #                     name="pat",
    #                     animated=True,
    #                     id="855023907383803945"
    #                 )
    #             )
    #         )
    #         await inter.send(
    #             content=(
    #                 "An error seems to have occurred!\n"
    #                 f"Traceback:\n{__import__('traceback').format_exc()}"
    #             ),
    #             hidden=True,
    #             view=view
    #         )
    @commands.Cog.listener()
    async def on_slash_command_error(self, inter, error):
        guild = self.bot.get_guild(852094131047104593)
        channel = guild.get_channel(852094131651870759)
        await channel.send(
            f"Traceback:\n{__import__('traceback').format_exc()}\n{error}"
        )
        view = View()
        view.add_item(
            discord.ui.Button(
                label="Support",
                url="https://izumibot.x10.mx/support",
                emoji=discord.PartialEmoji(
                    name="pat", animated=True, id="855023907383803945"
                ),
            )
        )
        if isinstance(error, commands.MissingPermissions):
            await inter.send(
                "You Can Not Use This Command.", hidden=True, view=View()
            )

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await inter.send(
                    "You Can Not Use This Command In A DM.",
                    hidden=True,
                    view=View(),
                )
            except discord.HTTPException:
                pass

        elif isinstance(error, commands.BotMissingPermissions):
            await inter.send(
                "Sorry, Izumi Does Not Have The Proper Perms To Execute This Command",
                hidden=True,
                view=View(),
            )
        elif isinstance(error, commands.CommandInvokeError):
            await inter.send(
                "Sorry, Izumi Does Not Have The Proper Perms To Execute This Command",
                hidden=True,
                view=View(),
            )

        else:
            pass


def setup(bot):
    bot.add_cog(Slashcmd(bot))
