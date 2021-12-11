# Future Imports
from __future__ import annotations

# Standard Library Imports
from typing import Optional, Union
import asyncio
import json
import logging

# Dependency Imports
from discord.ext import tasks
from dislash import *
from dislash.interactions import ActionRow, Button, ButtonStyle
from redbot.core import commands, Config
import aiohttp
import discord

# Music Imports
from .constants import (
    bfd_token,
    dbl_token,
    delly_token,
    Embed,
    fate_token,
    generatedailyembed,
    get_user,
    top_token,
    votedbotsfordiscord,
    votedTopgg,
)

log = logging.getLogger("red.mine.dbl")


class Dbl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.post_top_guilds.start()
        self.post_bfd_guilds.start()
        self.post_fate_guilds.start()
        self.post_dbl_guilds.start()
        self.post_delly_guilds.start()
        self.topgg_site = (
            f"[Click Here To Vote!](https://top.gg/bot/{self.bot.user.id})"
        )
        self.bfd_site = f"[Click Here To Vote!](https://botsfordiscord.com/bot/{self.bot.user.id})"
        self.void_bots_site = f"[Click Here To Vote!](https://voidbots.net/bot/{self.bot.user.id}/)"
        self.fateslist_bots_site = (
            "[Click Here To Vote!](https://fateslist.xyz/izumi/)"
        )

        self.config = Config.get_conf(
            self,
            identifier=798951566634778641,
            force_registration=True,
        )
        default_user = {"fatetoken": None}
        self.config.register_user(**default_user)

    def cog_unload(self):
        self.post_top_guilds.cancel()
        self.post_bfd_guilds.cancel()
        self.post_fate_guilds.cancel()
        self.post_dbl_guilds.cancel()
        self.post_delly_guilds.cancel()

    @commands.group()
    async def dbl(self, ctx: commands.Context):
        """Discord bot list commands"""

    @dbl.group()
    async def fate(self, ctx: commands.Context):
        """Fatelist commands"""

    @tasks.loop(minutes=30)
    async def post_delly_guilds(self):
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                "https://api.discordextremelist.xyz/v2/bot/{self.bot.user.id}/stats",
                headers={"Authorization": delly_token},
                data=json.dumps({"guildCount": len(self.bot.guilds)}),
            ) as resp:
                print(resp.status)
                log.debug("Posted DELLY guild count.")

    @post_delly_guilds.before_loop
    async def post_delly_guild_before(self):
        await self.bot.wait_until_red_ready()

    @post_delly_guilds.after_loop
    async def post_delly_guild_after(self):
        if self.post_delly_guilds.failed():
            log.exception("DELLY poster errored out, restarting")
            await asyncio.sleep(300)
            self.post_delly_guilds.restart()

    @tasks.loop(minutes=30)
    async def post_top_guilds(self):
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                "https://top.gg/api/bots/762976674659696660/stats",
                headers={"Authorization": top_token},
                json={"server_count": len(self.bot.guilds)},
            ) as resp:
                print(resp.status)
                log.debug("Posted TOP.GG guild count.")

    @post_top_guilds.before_loop
    async def post_top_guild_before(self):
        await self.bot.wait_until_red_ready()

    @post_top_guilds.after_loop
    async def post_top_guild_after(self):
        if self.post_top_guilds.failed():
            log.exception("TOP.GG poster errored out, restarting")
            await asyncio.sleep(300)
            self.post_top_guilds.restart()

    @tasks.loop(minutes=30)
    async def post_bfd_guilds(self):
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                "https://discords.com/bots/api/bot/762976674659696660",
                headers={"Authorization": bfd_token},
                json={"server_count": len(self.bot.guilds)},
            ) as resp:
                print(resp.status)
                log.debug("Posted BFD guild count.")

    @post_bfd_guilds.before_loop
    async def post_bfd_guild_before(self):
        await self.bot.wait_until_red_ready()

    @post_bfd_guilds.after_loop
    async def post_bfd_guild_after(self):
        if self.post_bfd_guilds.failed():
            log.exception("BFD poster errored out, restarting")
            await asyncio.sleep(300)
            self.post_bfd_guilds.restart()

    @tasks.loop(minutes=30)
    async def post_dbl_guilds(self):
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                "https://discordbotlist.com/api/v1/bots/762976674659696660/stats",
                headers={"Authorization": dbl_token},
                json={
                    "server_count": len(self.bot.guilds),
                    "user_count": len(self.bot.users),
                },
            ) as resp:
                print(resp.status)
                log.debug("Posted DBL guild count.")

    @post_dbl_guilds.before_loop
    async def post_dbl_guild_before(self):
        await self.bot.wait_until_red_ready()

    @post_dbl_guilds.after_loop
    async def post_dbl_guild_after(self):
        if self.post_dbl_guilds.failed():
            log.exception("BFD poster errored out, restarting")
            await asyncio.sleep(300)
            self.post_dbl_guilds.restart()

    @tasks.loop(minutes=30)
    async def post_fate_guilds(self):
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                "https://fateslist.xyz/api/v2/bots/762976674659696660/stats",
                headers={"Authorization": fate_token},
                json={
                    "guild_count": len(self.bot.guilds),
                    "user_count": len(self.bot.users),
                },
            ) as resp:
                print(resp.status)
                log.debug("Posted FATELIST guild count.")

    @post_fate_guilds.before_loop
    async def post_fate_guild_before(self):
        await self.bot.wait_until_red_ready()

    @post_fate_guilds.after_loop
    async def post_fate_guild_after(self):
        if self.post_fate_guilds.failed():
            log.exception("FATE poster errored out, restarting")
            await asyncio.sleep(300)
            self.post_fate_guilds.restart()

    @fate.command(aliases=["votec", "votes"])
    @commands.is_owner()
    async def votecount(self, ctx, user: discord.Member):
        """Only takes user ids"""
        async with aiohttp.ClientSession() as sess:
            async with sess.get(
                f"https://fateslist.xyz/api/v2/users/{user.id}/bots/762976674659696660/votes",
                headers={"Authorization": fate_token},
            ) as resp:
                origin = await resp.json()
                voted = origin["voted"]
                votes = origin["votes"]
                vote_r_n = origin["vote_right_now"]
                tt_vote = origin["time_to_vote"]

                embed = Embed()
                embed.add_field(
                    name="**{}'s Voting info:**".format(user),
                    value="Has Voted: {}\nAmount of votes: {}\nCan vote: {}".format(
                        voted,
                        votes,
                        vote_r_n,
                        tt_vote,
                    ),
                )

                await ctx.reply(embed=embed, mention_author=False)
                print(resp.status)

    @fate.command(name="vote")
    async def fate_vote(self, ctx):
        """Vote through the bot"""
        token_finder = await self.config.user(ctx.author).fatetoken()
        if token_finder is None:
            return await ctx.send("Please set a token")

        async with aiohttp.ClientSession() as sess:
            async with sess.patch(
                f"https://fateslist.xyz/api/v2/users/{ctx.author.id}/bots/762976674659696660/votes",
                headers={"Authorization": token_finder},
            ) as resp:
                origin = await resp.json()
                if resp.status == 200:
                    return await ctx.send(
                        "You have successfully voted, thank you!"
                    )
                else:
                    detail = origin["reason"]
                    embed = Embed(title="Vote failed")
                    embed.add_field(name="Details:", value=detail)
                    return await ctx.send(embed=embed)
                print(resp.status)

    @fate.command()
    @commands.dm_only()
    async def settoken(self, ctx, token: str):
        await self.config.user(ctx.author).fatetoken.set(token)
        await ctx.send("Your user token has successfully been set!")

    @fate.command()
    async def resettoken(self, ctx):
        await self.config.user(ctx.author).fatetoken.set(None)
        await ctx.send("Your user token has successfully been reset!")

    @fate.command()
    async def review(
        self,
        ctx,
        stars,
        review: str,
    ):
        """Review through the bot"""
        token_finder = await self.config.user(ctx.author).fatetoken()
        if token_finder is None:
            return await ctx.send("Please set a token")

        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                f"https://fateslist.xyz/api/v2/users/{ctx.author.id}/bots/762976674659696660/reviews",
                headers={"Authorization": token_finder},
                json={
                    "review": review,
                    "star_rating": stars,
                    "reply": False,
                },
            ) as resp:
                origin = await resp.json()
                if resp.status == 200:
                    return await ctx.send(
                        "You have successfully reviewed, thank you!"
                    )
                    print(resp.status)
                else:
                    detail = origin["reason"]
                    embed = Embed(title="Review failed")
                    embed.add_field(name="Details:", value=detail)
                    return await ctx.send(embed=embed)

    @commands.command()
    async def hasvoted(
        self, ctx, member: Optional[Union[int, discord.Member]] = None
    ):
        """Check if the user has voted or not"""
        member = get_user(ctx.author if not member else member, ctx)
        if member.bot:
            return await ctx.send("You **can't** check for a **bot account**")
        async with ctx.channel.typing():
            e = Embed(
                title=f"{member.display_name} vote stats for me",
                description=f"{member.mention} here your voting stats for last 12hours",
            )
            e.set_thumbnail(url=member.avatar.with_static_format("png").url)
            a = await self.session.get(
                f"https://top.gg/api/bots/{self.bot.user.id}/check",
                params={"userId": member.id},
                headers={"Authorization": top_token},
            )
            c = await self.session.get(
                f"https://discords.com/bots/api/bot/{self.bot.user.id}/votes",
                headers={"Authorization": bfd_token},
            )
            f = await self.session.get(
                f"https://fateslist.xyz/api/v2/bots/{self.bot.user.id}/votes",
                headers={"Authorization": fate_token},
                data={"user_id": member.id},
            )

            try:
                a_json = await a.json()
                a_list = True if a_json.get("voted") >= 1 else False
            except:
                a_list = False

            try:
                c_json = await c.json()
                c_list = (
                    True
                    if str(member.id) in c_json.get("hasVoted24", False)
                    else False
                )
            except:
                c_list = False

            try:
                f_json = await f.json()
                f1 = await f_json.json().get("voted", False)
            except:
                f1 = False

            e.add_field(
                name="**TopGG**",
                value=f"Voted : {self.topgg_site}"
                if a_list
                else f"Not Voted : {self.topgg_site}",
            )
            e.add_field(
                name="**BotsForDiscord**",
                value=f"Voted : {self.bfd_site}"
                if c_list
                else f"Not Voted : {self.bfd_site}",
            )
            e.add_field(
                name="**Fates List**",
                value=f"Voted : {self.fateslist_bots_site}"
                if f1
                else f"Not Voted : {self.fateslist_bots_site}",
            )
            await ctx.send(embed=e)

    # @commands.command()
    # async def payday(self, ctx: commands.Context):
    #     """Claim your rewards for voting!"""
    #     async with ctx.typing():
    #         if not votedbotsfordiscord(self, ctx) and not votedTopgg(
    #             self, ctx
    #         ):
    #             votes_list = [votedbotsfordiscord(), votedTopgg()]
    #             votes_list_name = ["botsfordiscord", "top.gg"]
    #             return await ctx.send(
    #                 embed=generatedailyembed(
    #                     ctx,
    #                     [
    #                         votes_list_name[i]
    #                         for i, k in enumerate(votes_list)
    #                         if not k
    #                     ],
    #                 )
    #             )
    #     await ctx.send("Success - TESTING")

    @commands.command()
    async def vote(self, ctx):
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
            text="Only Top.gg will give you currency rewards, but any vote is appreciated. ❤️"
        )
        await ctx.reply(
            embed=embed, components=my_buttons, mention_author=False
        )