# Future Imports
from __future__ import annotations

# Standard Library Imports
from random import choice, choices
from typing import Any, List
import asyncio
import json
import logging

# Dependency Imports
from discord.ext.commands import CheckFailure
from discord.ext.commands.errors import BadArgument
from redbot.core import bank, checks, commands, Config
from redbot.core.bot import Red
from redbot.core.data_manager import bundled_data_path, cog_data_path
from redbot.core.utils.chat_formatting import humanize_list
from redbot.core.utils.menus import commands, DEFAULT_CONTROLS, menu
from redbot.core.utils.predicates import MessagePredicate
import discord

Cog: Any = getattr(commands, "Cog", object)


class Gacha(Cog):
    """Marry anime characters?!"""

    __author__ = "Onii-Chan"
    __version__ = "0.1.0"

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=31695032120066669, force_registration=True
        )

        self.config.register_user(inventory={}, wishlies={})

        self.config.register_guild(toggle=True, rollprice=1000)

    async def _send_message(channel, message):
        """Sends a message"""

        em = discord.Embed(description=message, color=discord.Color.green())
        await channel.send(embed=em)

    async def _load_card_list(self):
        """reloads the card list"""
        card_data_fp = bundled_data_path(self) / "default" / "cards.json"
        with card_data_fp.open() as json_data:
            self.card_data = json.load(json_data)

    async def _grab_random_rarity(self):
        """grabs a random rarity"""
        # EVERYTIME YOU ADD A RARITY, BE SURE TO ADD IT HERE AND WEIGHT IT
        raritylist = [
            "normal",
            "rare",
            "super rare",
            "super super rare",
            "ultra rare",
        ]
        raritygrabbed = choices(raritylist, weights=[40, 50, 8, 2, 1])
        raritystring = raritygrabbed[0]
        return raritystring

    @commands.group(autohelp=True)
    @checks.admin_or_permissions(manage_guild=True)
    async def gachaset(self, ctx):
        """Settings for this gacha"""
        pass

    @gachaset.command(name="toggle")
    async def gachaset_toggle(
        self, ctx: commands.Context, on_off: bool = None
    ):
        """Toggle Gacha System for server
        If 'on_off' is not provided, the state will be flipped."""
        target_state = (
            on_off
            if on_off
            else not (await self.config.guild(ctx.guild).toggle())
        )
        await self.config.guild(ctx.guild).toggle.set(target_state)
        if target_state:
            await ctx.send("Gacha System is now enabled.")
        else:
            await ctx.send("Gacha System is now disabled.")

    @checks.is_owner()
    @gachaset.command(name="rollprice")
    async def gachaset_rollprice(self, ctx: commands.Context, price: int):
        """Set the price for rolling"""

        if price <= 0:
            await ctx.send("Oh no! That puts me in a debt.")
        await self.config.guild(ctx.guild).rollprice.set(price)
        await ctx.tick()

        #        @commands.command()
        #        async def wish(self, ctx: commands.Context, card: card.name = None):
        #            """Add a card to your wishlist"""

        #        if not await self.config.guild(ctx.guild).toggle():
        #            return await ctx.send("Bitch, you can't gacha in this server")
        #        if not card:
        #            await self.configmember(ctx.quthor).wishlist.set(None)

    @commands.command()
    async def gacharoll(self, ctx: commands.Context, amount: int = 1):
        """pulls a card from the current card list"""
        await self._load_card_list()
        author = ctx.author
        totalcost = self.config.guild(ctx.guild).rollprice()

        # every ten rolls, give grant 1 extra roll!
        if int(amount / 10) >= 1:
            amount += int(amount / 10)

        # Creates a rarity list, and then give it weights so that more common are more common
        raritylist = [
            "normal",
            "rare",
            "super rare",
            "super super rare",
            "ultra rare",
        ]
        raritygrabbed = choices(
            raritylist, weights=[40, 50, 7, 2, 1], k=amount
        )

        # Start creating pages for the embed command
        allcard = []
        titlepage = discord.Embed(
            title=f"{author.mention}", description="Rolls"
        )
        url = "https://scontent-syd2-1.xx.fbcdn.net/v/t1.6435-9/189248135_4375541332480004_7956546107304077431_n.jpg?_nc_cat=110&ccb=1-5&_nc_sid=8bfeb9&_nc_ohc=Zg2DD2Z-9YgAX80HNtc&_nc_ht=scontent-syd2-1.xx&oh=fbb71b0e1cee48be8d4eb37a2f27496f&oe=6167E1D3"
        titlepage.set_thumbnail(url=url)
        titlepage.add_field(
            name="Total cards", value=str(amount), inline=False
        )
        titlepage.add_field(
            name="Total cost", value=str(totalcost), inline=False
        )
        titlepage.set_footer(text="Use the arrows to navigate")
        allcard.append(titlepage)

        await ctx.send("You've rolled " + str(amount) + " of times")
        for x in range(0, amount):
            raritystring = raritygrabbed[x]
            # grabs a rarity from the rarity list above
            card_options = self.card_data[raritystring]

            # Grabs a random card of the rarity grabbed and then creates the embed card for that card
            cardrolled = choice(card_options)
            embed = discord.Embed(
                title=cardrolled["name"], description=cardrolled["series"]
            )
            embed.set_thumbnail(url=cardrolled["image"])
            embed.add_field(name="Rarity", value=raritystring, inline=False)
            embed.add_field(
                name="Birthday", value=cardrolled["birthday"], inline=False
            )
            embed.add_field(
                name="Quote", value=cardrolled["quote"], inline=False
            )
            embed.add_field(
                name="page",
                value=str(x) + " out of " + str(amount),
                inline=False,
            ),
            embed.set_footer(text="You want another Gacha hit don't you?")

            # adds the card to the pages
            allcard.append(embed)
        # Print out the pages as a menu (pages doesn't work for some reason)
        await menu(
            ctx,
            pages=allcard,
            controls=DEFAULT_CONTROLS,
            message=None,
            page=0,
            timeout=60,
        )
