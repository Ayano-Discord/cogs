# from _typeshed import StrOrBytesPath
# from os import name
# Future Imports
from __future__ import annotations

# Standard Library Imports
from datetime import timezone
import asyncio
import datetime
import json
import random
import re
import time

# Dependency Imports
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from discord.ext import tasks
from redbot.core import commands
import discord

# def convert(date):
#     pos = ["s", "m", "h", "d"]
#     time_dic = {"s": 1, "m": 60, "h": 3600, "d": 3600 * 24}
#     i = {"s": "Secondes", "m": "Minutes", "h": "Heures", "d": "Jours"}
#     unit = date[-1]
#     if unit not in pos:
#         return -1
#     try:
#         val = int(date[:-1])

#     except:
#         return -2

#     if val == 1:
#         return val * time_dic[unit], i[unit][:-1]
#     else:
#         return val * time_dic[unit], i[unit]

time_regex = re.compile(r"(?:(\d{1,5})(h|s|m|d))+?")
time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}


def convert(argument):
    args = argument.lower()
    matches = re.findall(time_regex, args)
    time = 0
    for key, value in matches:
        try:
            time += time_dict[value] * float(key)
        except KeyError:
            raise commands.BadArgument(
                f"{value} is an invalid time key! h|m|s|d are valid arguments"
            )
        except ValueError:
            raise commands.BadArgument(f"{key} is not a number!")
    return round(time)


async def stop_giveaway(self, g_id, data):
    channel = self.bot.get_channel(data["channel_id"])
    giveaway_message = await channel.fetch_message(int(g_id))
    users = await giveaway_message.reactions[0].users().flatten()
    users.pop(users.index(self.bot.user))
    if len(users) < data["winners"]:
        winners_number = len(users)
    else:
        winners_number = data["winners"]
    # data.update({"ended": True})
    winners = random.sample(users, winners_number)
    users_mention = []
    for user in winners:
        users_mention.append(user.mention)
    result_embed = discord.Embed(
        title="🎉 {} 🎉".format(data["prize"]),
        color=self.color,
        description="Congratulations {} you won the giveaway !".format(
            ", ".join(users_mention)
        ),
    )
    result_embed.set_footer(
        icon_url=self.bot.user.avatar.url, text="Giveaway Ended !"
    )
    await giveaway_message.edit(embed=result_embed)
    await channel.send(
        ", ".join(users_mention)
        + " you have won the giveaway for {}".format(data["prize"])
    )
    #    await ghost_ping.delete()
    giveaways = json.load(
        open("/home/ubuntu/mine/giveaway/giveaways.json", "r")
    )
    new_data = {
        "prize": giveaways[g_id]["prize"],
        "host": giveaways[g_id]["host"],
        "winners": giveaways[g_id]["winners"],
        "end_time": giveaways[g_id]["end_time"],
        "del_time": giveaways[g_id]["del_time"],
        "channel_id": giveaways[g_id]["channel_id"],
        "ended": True,
        "message_id": giveaways[g_id]["message_id"],
    }
    giveaways[str(giveaways[g_id]["message_id"])] = new_data
    json.dump(
        giveaways,
        open("/home/ubuntu/mine/giveaway/ended_giveaways.json", "w"),
        indent=4,
    )
    giveaways1 = json.load(
        open("/home/ubuntu/mine/giveaway/giveaways.json", "r ")
    )
    del giveaways1[g_id]
    json.dump(
        giveaways1,
        open("/home/ubuntu/mine/giveaway/giveaways.json", "w"),
        indent=4,
    )


class GiveawayAborted(Exception):
    pass


class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = 0xF295A4
        self.giveaway_task.start()
        self.giveaway_deleter.start()

    def cog_unload(self):
        self.giveaway_task.cancel()
        self.giveaway_deleter.cancel

    @tasks.loop(seconds=5)
    async def giveaway_task(self):
        await self.bot.wait_until_red_ready()
        giveaways = json.load(
            open("/home/ubuntu/mine/giveaway/giveaways.json", "r")
        )
        if len(giveaways) == 0:
            return
        for giveaway in giveaways:
            data = giveaways[giveaway]
            if int(time.time()) > data["end_time"]:
                # if not giveaways[giveaway]["ended"] == False:
                #     return
                await stop_giveaway(self, giveaway, data)
                # data["ended"] = True

    @tasks.loop(seconds=300)
    async def giveaway_deleter(self):
        await self.bot.wait_until_red_ready()
        giveaways = json.load(
            open("/home/ubuntu/mine/giveaway/giveaways.json", "r")
        )

        if len(giveaways) == 0:
            return

        for giveaway in giveaways:
            data = giveaways[giveaway]
            if int(time.time()) > data["del_time"]:
                g_id = data["message_id"]
                del giveaways[g_id]

    @commands.command(
        name="giveaway",
        aliases=["gstart"],
        # invoke_without_subcommand=True
    )
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx: commands.Context):
        init = await ctx.send(
            embed=discord.Embed(
                title="🎉 Setup Wizard! 🎉",
                description=(
                    "You have initiated the giveaway interactive menu. "
                    "You have 60 seconds to answer each question and you "
                    "can cancel this anytime by replying with `cancel` to any "
                    "question."
                ),
                color=self.color,
            ).set_footer(
                icon_url=self.bot.user.avatar.url, text=self.bot.user.name
            )
        )
        questions = [
            "What would be the prize of the giveaway?",
            "Please mention or type the channel's ID or the name where the giveaway will be hosted!",
            """Please type the giveaway's duration.

            If you want to enter multiple arguments, seperate them with spaces. Ex: 1h 60m 3600s | Any invalid argument will be ignored

            You can use:
            s = seconds
            m = Minutes
            h = hours
            d = days""",
            "How many winners do you want for this Giveaway?",
        ]

        def check(message):
            if message.author.id != ctx.author.id:
                return False
            if message.channel != ctx.channel:
                return False
            if message.content.lower() == "cancel":
                raise GiveawayAborted()
            return True

        index = 1
        answers = []
        question_message = None
        for question in questions:
            embed = discord.Embed(
                title="Giveaway Question {}".format(index),
                description=question,
                color=self.color,
            ).set_footer(icon_url=self.bot.user.avatar.url, text="Giveaway !")
            if index == 1:
                question_message = await ctx.send(embed=embed)
            else:
                await question_message.edit(embed=embed)

            try:
                user_response = await self.bot.wait_for(
                    "message", timeout=120, check=check
                )
                try:
                    await user_response.delete()
                except discord.errors.Forbidden:
                    pass
            except asyncio.TimeoutError:
                await ctx.send(
                    embed=discord.Embed(
                        title="Error",
                        color=self.color,
                        description="You took too long to answer this question",
                    )
                )
                return
            else:
                if user_response == "cancel":
                    return await ctx.send("Giveaway creation canceled...")
                else:
                    pass
                answers.append(user_response.content)
                index += 1
        try:
            channel_id = int(answers[1][2:-1])
        except ValueError:
            msg = (
                "You didn't mention the channel correctly, do it like {}."
            ).format(ctx.channel.mention)
            await ctx.send(msg)
            return

        try:
            winners = abs(int(answers[3]))
            if winners == 0:
                await ctx.send("You did not enter an postive number.")
                return
        except ValueError:
            await ctx.send("You did not enter an integer.")
            return
        prize = answers[0].title()
        channel = self.bot.get_channel(channel_id)
        converted_time = convert(answers[2])
        if converted_time == -1:
            await ctx.send(
                "You did not enter the correct unit of time (s|m|d|h)"
            )
        elif converted_time == -2:
            await ctx.send("Your time value should be an integer.")
            return
        await init.delete()
        await question_message.delete()
        giveaway_embed = discord.Embed(
            title="<:giveaway:894419983419969587> {}".format(prize),
            color=self.color,
            description=(
                f'» **{winners}** {"winner" if winners == 1 else "winners"}\n'
                f"» Hosted by {ctx.author.mention}\n\n"
                "» **React with 🎉 to get into the giveaway.**\n"
            ),
        )
        giveaway_embed.set_footer(
            icon_url=self.bot.user.avatar.url,
            text="By reacting you agree to be dmed\nHost: {}{}".format(
                ctx.author.name, ctx.author.discriminator
            ),
        )

        # giveaway_embed.timestamp = datetime.datetime.utcnow() + datetime.timedelta(
        #     seconds=converted_time[0]
        # )
        giveaway_message = await channel.send(embed=giveaway_embed)
        await giveaway_message.add_reaction("🎉")
        now = int(time.time())
        month = datetime.datetime.fromtimestamp(now)
        date_format = month.strftime("%m/%d/%Y %H:%M:%S")
        date_format_parse = parse(date_format)
        future_date = date_format_parse + relativedelta(months=1)
        future_date_utc = future_date.replace(tzinfo=timezone.utc).timestamp()
        # server = json.load(open("/home/ubuntu/mine/giveaway/giveaways.json", "r"))
        # sdata = {}
        # server[str(ctx.guild.id)] = sdata
        # json.dump(server, open("/home/ubuntu/mine/giveaway/giveaways.json", "w"), indent=4)
        giveaways = json.load(
            open("/home/ubuntu/mine/giveaway/giveaways.json", "r")
        )
        data = {
            "prize": prize,
            "host": ctx.author.id,
            "winners": winners,
            "end_time": now + converted_time[0],
            "del_time": future_date_utc,
            "channel_id": channel.id,
            "ended": False,
            "message_id": giveaway_message.id,
        }
        giveaways[str(giveaway_message.id)] = data
        json.dump(
            giveaways,
            open("/home/ubuntu/mine/giveaway/giveaways.json", "w"),
            indent=4,
        )

    @commands.command(
        name="gstop",
        # aliases=["gstop"],
        # usage="{giveaway_id}"
    )
    @commands.has_permissions(manage_guild=True)
    async def gstop(self, ctx: commands.Context, message_id: str):
        await ctx.message.delete()
        giveaways = json.load(
            open("/home/ubuntu/mine/giveaway/giveaways.json", "r")
        )
        if message_id not in giveaways.keys():
            return await ctx.send(
                embed=discord.Embed(
                    title="Error",
                    description=(
                        "Oh no! I can't find that giveaway in my database, "
                        "please check the ID and try again."
                    ),
                    color=self.color,
                )
            )
        await stop_giveaway(self, message_id, giveaways[message_id])

    @commands.command(name="greroll")
    @commands.has_permissions(manage_guild=True)
    async def greroll(
        self, ctx: commands.Context, message_id: str, winners: int = None
    ):
        giveaways = json.load(
            open("/home/ubuntu/mine/giveaway/ended_giveaways.json", "r")
        )
        data = giveaways[message_id]
        channel = self.bot.get_channel(data["channel_id"])
        giveaway_message = await channel.fetch_message(int(message_id))
        users = await giveaway_message.reactions[0].users().flatten()
        users.pop(users.index(self.bot.user))
        if winners is not None:
            winners_number = winners
        else:
            winners_number = data["winners"]
        winners = random.sample(users, winners_number)
        users_mention = []
        for user in winners:
            users_mention.append(user.mention)
        if message_id not in giveaways.keys():
            return await ctx.send(
                embed=discord.Embed(
                    title="Error",
                    description=(
                        "Oh no! I can't find that giveaway in my database, "
                        "that giveaway might have been deleted from "
                        "my database, or hasn't ended yet.\n\n"
                        "If your giveaway has ended and this command doesn't "
                        "work, please post a screenshot of the ended giveaway "
                        "in the "
                        "[support server](https://izumibot.x10.mx/support)"
                    ),
                    color=self.color,
                )
            )
        winner_amount = f'{"winner" if winners_number == 1 else "winners"}'
        is_are = f'{"is" if winners_number == 1 else "are"}'
        message_str = "{} {} the new {} for the giveaway '{}'".format(
            ", ".join(users_mention),
            is_are,
            winner_amount,
            giveaways[message_id]["prize"],
        )
        await ctx.reply(message_str)

    @commands.is_owner()
    @commands.command(name="giveawaystats", aliases=["gstats"])
    async def giveawaystats(self, ctx: commands.Context):
        ongoing_giveaways = json.load(
            open("/home/ubuntu/mine/giveaway/giveaways.json", "r")
        )
        ended_giveaways = json.load(
            open("/home/ubuntu/mine/giveaway/ended_giveaways.json", "r")
        )
        embed = discord.Embed(title="Giveaway Stats!\n", colour=self.color)
        embed.add_field(
            name="On-going Giveaway stats:",
            value=f"Number of on-going giveaways: {len(ongoing_giveaways)}",
            inline=False,
        )
        embed.add_field(
            name="Ended giveaway stats:",
            value=f"Ending giveaways: {len(ended_giveaways)}",
            inline=False,
        )
        await ctx.send(embed=embed)

    # @commands.command()
    # async def gtest(self, ctx: commands.Context, user: discord.User = None):
    #     if user is None:
    #         user = ctx.author
    #     giveaways = json.load(
    #         open(
    #             "/home/ubuntu/mine/giveaway/test.json",
    #             "r"
    #         )
    #     )
    #     data = {
    #         "msg": "message1",
    #     }
    #     giveaways[str(ctx.guild.id)][str(user.id)] = data
    #     json.dump(giveaways, open("/home/ubuntu/mine/giveaway/test.json", "w"), indent=4)


def setup(bot):
    bot.add_cog(Giveaways(bot))


# <h1 id="superbot-privacy-policy">SuperBot Privacy Policy</h1>
# <h3 id="message-tracking">Message Tracking</h3>
# <p>SuperBot comes with automoderation tools that tracks every message sent by every user in every channel the bot has access to. It does NOT store any messages locally and if the logging channels are set up, sends the log messages there. A few example usages of this message tracking is the auto filtering of scam links (To know more execute the following command: <code>!help ScamChecker</code>) and if reTrigger is enabled, then it checks every message for potential trigger-phrases.</p>
# <h3 id="userdata-tracking">UserData Tracking</h3>
# <p><strong>SuperBot has several modules and you can find the user-data usage information by executing the following command:</strong></p>
# <p><code>!help mydata</code></p>
# <p><strong>To view the End User Data statements of the 3rd party modules, execute the following command:</strong></p>
# <p><code>!mydata 3rdparty</code></p>
# <p>This command will list all the modules that use and don&#39;t use user data in an HTML file to read the statements with ease.</p>
# <p><strong>To make SuperBot forget what it knows about you, execute the following command:</strong></p>
# <p><code>!mydata forgetme</code></p>
# <p><strong>[Coming soon] Ability to get your data</strong></p>
# <p>This feature is being implemented and will be available soon. You can request all the data SuperBot has about you soon.</p>
# <p><strong>To get further support, please use the following command to contact me (WreckRox#3064) via the bot:</strong></p>
# <p><code>!contact</code></p>
# <p>This file can and will be updated as necessary.</p>
