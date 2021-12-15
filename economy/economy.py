# Future Imports
from __future__ import annotations

# Standard Library Imports
from datetime import timezone
from random import randint
import asyncio
import datetime
import sys

sys.path.insert(1, "/home/ubuntu/mine/premium")

# Standard Library Imports
import json
import logging
import random
import time

# Dependency Imports
from checks import is_premium
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from redbot.cogs.economy import Economy as EconomyClass
from redbot.core import bank, commands
from redbot.core.config import Value
from redbot.core.errors import BalanceTooHigh
from redbot.core.utils.predicates import MessagePredicate
import discord

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

    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

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

    @commands.command(name="loan")
    async def loan(self, ctx, amount: int):
        """Take a loan from the bank!"""
        # print("I got this far!0")
        if is_premium:
            limit = 1000000
        #        print("I got this far!")
        else:
            limit = 500000
        # print("I got this far!")

        def check(msg):
            return (
                msg.content.lower().startswith("y")
                and msg.author.id == ctx.author.id
            )

        # print("I got this far!2")
        if amount > limit:
            await ctx.reply(
                "Oops! I don't want to be bankrupt! Please try an amount **smaller** than {}!".format(
                    limit
                )
            )
            return
        # print("I got this far!3")
        if not is_premium:
            interest_rate = random.randint(2.8, 3.5)
            interest = amount * interest_rate
        else:
            interest = amount
        # print("I got this far!4")
        await ctx.send(
            "Are you sure you wanna take a loan of {}, You'll have 1 month to pay it back.\n**Reply with yes/y to confirm or no/n to cancel.**"
        )
        try:
            msg = await self.bot.wait_for("message", timeout=10, check=check)
            if msg:
                now = int(time.time())
                month = datetime.datetime.fromtimestamp(now)
                date_format = month.strftime("%m/%d/%Y %H:%M:%S")
                date_format_parse = parse(date_format)
                #  print("I got this far!5")
                future_date = date_format_parse + relativedelta(months=1)
                future_date_utc = future_date.replace(
                    tzinfo=timezone.utc
                ).timestamp()
                # print("I got this far!6")
                loans = json.load(
                    open("/home/ubuntu/mine/economy/dicts/loans.json", "r")
                )
                # print("I got this far!7")
                data = {
                    "user_id": ctx.author.id,
                    "loan_amount": amount,
                    "interest": interest,
                    "end_time": future_date_utc,
                }
                loans[str(ctx.author.id)] = data
                # print("I got this far!8")
                json.dump(
                    loans,
                    open("/home/ubuntu/mine/economy/dicts/loans.json", "w"),
                    indent=4,
                )
                # print("I got this far!9")
                await bank.deposit_credits(amount)
                bank_bal = await bank.get_balance(ctx.author)
                # print("I got this far!10")
                success_string = (
                    "{} Has been added to your account, your new balance is {}.\n"
                    "**You have 1 month to pay back your loan"
                    "before you're automatically blacklisted.**\n\n"
                    "Enjoy!"
                ).format(amount, bank_bal)
                # print("I got this far!11")
                await ctx.send(success_string)
                # print("I got this far!12")

        except asyncio.TimeoutError:
            return await ctx.send("Cancelling...")

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


async def setup(bot):
    cog = Economy(bot)
    global work
    work = bot.remove_command("work")
    bot.add_cog(cog)


#    await cog.initialize()
