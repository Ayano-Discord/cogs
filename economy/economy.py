# Future Imports
from __future__ import annotations

# Standard Library Imports
from collections import defaultdict
from datetime import timezone
from random import randint
import asyncio
import datetime
import json
import logging
import random
import sys
import time

# Dependency Imports
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from redbot.cogs.economy import Economy as EconomyClass
from redbot.core import bank, commands, Config
from redbot.core.config import Value
from redbot.core.errors import BalanceTooHigh
from redbot.core.utils.predicates import MessagePredicate
import discord
import humanize

# Music Imports
from .constants import job_list

log = logging.getLogger("red.cogs.economy")


class Economy(EconomyClass):
    """Ecnomy commands for Izumi!"""

    def cog_unload(self):
        global work
        if work:
            try:
                self.bot.remove_command("work")
            except Exception as e:
                log.info(e)
            self.bot.add_command(work)
        if self.startup_task:
            self.startup_task.cancel()

    default_guild_settings = {
        "PAYDAY_TIME": 300,
        "PAYDAY_CREDITS": 120,
        "SLOT_MIN": 5,
        "SLOT_MAX": 100,
        "SLOT_TIME": 5,
        "REGISTER_CREDITS": 0,
    }

    default_global_settings = default_guild_settings

    default_member_settings = {
        "next_payday": 0,
        "last_slot": 0,
        "daily_cooldowns": {
            "daily_cooldown": 0,
            "weekly_cooldown": 0,
            "monthly_cooldown": 0,
        },
    }

    default_role_settings = {"PAYDAY_CREDITS": 0}

    default_user_settings = default_member_settings

    def __init__(self, bot):

        super().__init__(bot)
        self.bot = bot
        self.config = Config.get_conf(self, 1256844281)
        self.config.register_guild(**self.default_guild_settings)
        self.config.register_global(**self.default_global_settings)
        self.config.register_member(**self.default_member_settings)
        self.config.register_user(**self.default_user_settings)
        self.config.register_role(**self.default_role_settings)
        self.slot_register = defaultdict(dict)

    @commands.command()
    @commands.cooldown(1, 600, commands.BucketType.user)
    async def work(self, ctx):
        with open("/home/ubuntu/mine/economy/dicts/jobs.json") as fp:
            data = json.load(fp)
            joblist = ["detective", "chef"]
            questionlist = ["1", "2", "3"]
            jobchooser = random.choice(joblist)
            jobs = data[jobchooser]
            random_index = randint(0, len(jobs) - 1)
            question = random.choice(questionlist)
            questions = jobs[random_index][question]
            jobtext = jobs[random_index]["jobtext"]
            emoji = jobs[random_index][f"e{question}"]
            timeoutstring = jobs[random_index]["timeout_string"]
            answer_string = jobs[random_index][f"a{question}"]
            answer_string2 = answer_string.replace(" ", "")
        await ctx.send(f"{jobtext}".format(emoji))
        msg = await ctx.send(f"{questions}", delete_after=3)
        # answer = questions.replace(":", "")
        # v = random.choice(list(job_list.keys()))

        # v1 =  job_list.get(v)

        # await ctx.send(v1)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            message = await self.bot.wait_for(
                "message", timeout=15, check=check
            )
            answers_list = answer_string or answer_string2
            if message.content == answers_list:
                earnt_umi = random.randint(500, 2000)
                await bank.deposit_credits(ctx.author, earnt_umi)
                return await ctx.send(f"You have earned `{earnt_umi}`")
            else:
                return await ctx.send(f"{timeoutstring}")
        except asyncio.TimeoutError:
            return await ctx.send(f"{timeoutstring}")

    # @commands.command()
    # @commands.cooldown(1, 1800, commands.BucketType.user)
    # async def beg(self, ctx):
    #     with open("/home/ubuntu/mine/izonomy/dicts/beg.json") as fp:
    #         data = json.load(fp)
    #         questionlist = ["-", "+"]
    #         begchooser = random.choice(questionlist)
    #         beg_t = data[begchooser]
    #         random_index = randint(0, len(beg_t) - 1)
    #         question = random.choice(questionlist)
    #         questions = jobs[random_index][question]
    #         jobtext = jobs[random_index]["jobtext"]
    #         emoji = jobs[random_index][f"e{question}"]
    #         timeoutstring = jobs[random_index]["timeout_string"]
    #         answer_string = jobs[random_index][f"a{question}"]
    #     await ctx.send(f"{jobtext}".format(emoji))
    #     await ctx.send(f"{questions}", delete_after=3)

    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def lottery(self, ctx):
        """
        Pay 10000 to enter the lottery, you have a 1/1980000099 chance of winning!

        You can walk away with 2 million umi's if you win.

        Good luck!
        """
        string = (
            "Are you sure you want to enter the lottery?\n"
            "**You'll be charged 10000 to enter**\n"
            "\nEnter `yes` or `no`"
        )
        await ctx.send(string)

        def lottcheck(msg):
            return (
                msg.content.lower().startswith("y")
                and msg.author.id == ctx.author.id
            )

        try:
            msg = await self.bot.wait_for(
                "message", timeout=10, check=lottcheck
            )
            if msg:
                try:
                    await bank.withdraw_credits(ctx.author, 10000)
                except ValueError:
                    user_balance = bank.get_balance(ctx.author)
                    return await ctx.send(
                        "Oh no! You don't have enogh umis to enter the lottery, you need to have 10000 but you only have {}".format(
                            user_balance
                        )
                    )
                amount = random.randrange(100000, 2000000)
                chance = round(random.uniform(0.01, 20000000.99), 2)
                lotto_msg = await ctx.send("Drawing the lotto")
                await asyncio.sleep(1)
                await lotto_msg.edit("Drawing the lotto.")
                await asyncio.sleep(1)
                await lotto_msg.edit("Drawing the lotto..")
                await asyncio.sleep(1)
                await lotto_msg.edit("Drawing the lotto...")
                await asyncio.sleep(1)
                await lotto_msg.edit("Drawing the lotto")
                await asyncio.sleep(1)
                await lotto_msg.edit("Drawing the lotto.")
                await asyncio.sleep(1)
                await lotto_msg.edit("Drawing the lotto..")
                await asyncio.sleep(1)
                await lotto_msg.edit("Drawing the lotto...")
                if chance == 12459823.23:
                    await lotto_msg.edit(
                        f"Congrats!!!\n\nYou won the lottery and got {amount} umis"
                    )
                    guild = self.bot.get_guild(852094131047104593)
                    channel = guild.get_channel(852094131550552092)
                    await channel.send(
                        f"<@741291562687922329>\n{ctx.author.mention} just won the lotto! They took home {amount}!!"
                    )
                    await bank.deposit_credits(ctx.author, amount)
                    return
                else:
                    await lotto_msg.edit(
                        "Sooo close!!\nPlay again for the chance to win over 2 million umis!!"
                    )
                    return
            else:
                await ctx.send("Cancelling...")
                return
        except asyncio.TimeoutError:
            await ctx.send("Cancelling...")
            return

    @commands.command(name="transfer")
    @commands.cooldown(1, 3600, commands.BucketType.user)
    @commands.guild_only()
    async def transfer(
        self,
        ctx,
        user: discord.Member,
        amount: int = 10000,
    ):
        """
        Transfer some of your money to another user.

        <amount> is the amount you want to transfer, if this isnt specified, it will default to 10000
        <user> is the user you want to transfer the money to
        """

        #  if user is None:
        #     return await ctx.reply(
        #         "Oh no! You didnt specify a user, please specify a user and try again!",
        #         mention_author=False
        #     )
        # yes_string = "yes", "y"
        # no_string = "no" or "n" or "cancel"

        # def check(m):
        # return m.author == ctx.author and m.channel == ctx.channel

        pred = MessagePredicate.yes_or_no(ctx)

        try:
            await ctx.send(
                "Are you sure you want to transfer {} to {}?\n\n**Reply with yes/y to confirm or no/n to cancel**".format(
                    amount, user.mention
                )
            )
            await self.bot.wait_for("message", timeout=10, check=pred)
        except asyncio.TimeoutError:
            return await ctx.reply(
                "You took too long to repond! Please try again later."
            )
        if pred.result is True:
            try:
                await bank.transfer_credits(ctx.author, user, amount)
            except ValueError:
                user_balance = await bank.get_balance(ctx.author)
                return await ctx.send(
                    "Oh no! You are trying to tranfer {} umis, but you only have {}".format(
                        amount, user_balance
                    )
                )
            except BalanceTooHigh:
                return await ctx.send(
                    "Oopsie! {} you are tranferring the credits has already reached the maxium amount of umis allowed!".format(
                        user.mention
                    )
                )
            else:
                author_bal = await bank.get_balance(ctx.author)
                user_balance = await bank.get_balance(user)
                await ctx.send(
                    "{} umis have been successfully transferred to {}.\nYour new balance is {} umis and {}'s balance is {} umis".format(
                        amount,
                        user.mention,
                        author_bal,
                        user.mention,
                        user_balance,
                    )
                )
        else:
            return await ctx.send("Cancelling...")

    @commands.command(name="daily")
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.guild_only()
    async def _daily(self, ctx):
        """
        Get your daily umis!

        You can only get your daily umis once per day.
        """
        user = ctx.author
        daily_bal = await self.config.user(
            ctx.author
        ).daily_cooldowns.daily_cooldown()
        if daily_bal > 0:
            return await ctx.send(
                "You already got your daily umis! You can get your daily umis again in {}".format(
                    humanize.naturaldelta(
                        datetime.datetime.utcnow()
                        + datetime.timedelta(hours=24)
                        - datetime.datetime.utcnow()
                    )
                )
            )
        else:
            amount = random.randrange(100, 500)
            await bank.deposit_credits(user, amount)
            await ctx.send(
                "You got your daily umis! You now have {} umis".format(
                    await bank.get_balance(user)
                )
            )


async def setup(bot):
    cog = Economy(bot)
    global work
    work = bot.remove_command("work")
    bot.add_cog(cog)


#    await cog.initialize()
