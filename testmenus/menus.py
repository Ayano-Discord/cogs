# Future Imports
from __future__ import annotations

# Standard Library Imports
from typing import Callable, List

# Dependency Imports
from redbot.core import commands
from redbot.core.commands.help.help_menu import MainHelp
from redbot.vendored.discord.ext import menus
import discord


class MenuSource(menus.ListPageSource):
    def __init__(self, methods: List[Callable]):
        super().__init__(methods, per_page=1)

    async def format_page(
        self, menu: HelpMenu, entry: Callable
    ) -> discord.Embed:
        return await entry(menu.ctx)


class HelpMenu(menus.MenuPages, inherit_buttons=False):
    def reaction_check(self, payload):
        """The function that is used to check whether the payload should be processed.
        This is passed to :meth:`discord.ext.commands.Bot.wait_for <Bot.wait_for>`.

        There should be no reason to override this function for most users.

        Parameters
        ------------
        payload: :class:`discord.RawReactionActionEvent`
            The payload to check.

        Returns
        ---------
        :class:`bool`
            Whether the payload should be processed.
        """
        if payload.message_id != self.message.id:
            return False
        if payload.user_id not in (*self.bot.owner_ids, self._author_id):
            return False

        return payload.emoji in self.buttons

    def _can_send_custom(self):
        permissions = self.ctx.channel.permissions_for(self.ctx.me)
        return permissions.external_emojis

    def _can_not_send_custom(self):
        permissions = self.ctx.channel.permissions_for(self.ctx.me)
        return not permissions.external_emojis

    @menus.button("\N{MUSICAL NOTE}", position=menus.First(0))
    async def music_page(self, payload: discord.RawReactionActionEvent):
        await self.show_checked_page(1)

    @menus.button("\N{THOUGHT BALLOON}", position=menus.First(1))
    async def general_page(self, payload: discord.RawReactionActionEvent):
        await self.show_checked_page(2)

    @menus.button("\N{VIDEO GAME}", position=menus.First(2))
    async def games_page(self, payload: discord.RawReactionActionEvent):
        await self.show_checked_page(3)

    @menus.button("\N{FRAME WITH PICTURE}", position=menus.First(3))
    async def images_page(self, payload: discord.RawReactionActionEvent):
        await self.show_checked_page(4)

    @menus.button("\N{NO ONE UNDER EIGHTEEN SYMBOL}", position=menus.First(4))
    async def nsfw_page(self, payload: discord.RawReactionActionEvent):
        await self.show_checked_page(5)

    @menus.button("\N{HAMMER AND WRENCH}", position=menus.First(5))
    async def mods_page(self, payload: discord.RawReactionActionEvent):
        await self.show_checked_page(6)

    @menus.button("\N{GEAR}", position=menus.First(6))
    async def utils_page(self, payload: discord.RawReactionActionEvent):
        await self.show_checked_page(7)

    @menus.button("\N{CLIPBOARD}", position=menus.First(7))
    async def infos_page(self, payload: discord.RawReactionActionEvent):
        await self.show_checked_page(8)

    @menus.button("\N{BLACK LEFT-POINTING TRIANGLE}", position=menus.First(8))
    async def prev(self, payload: discord.RawReactionActionEvent):
        await self.show_checked_page(self.current_page - 1)

    @menus.button("\N{HOUSE BUILDING}", position=menus.First(9))
    async def first_page(self, payload: discord.RawReactionActionEvent):
        await self.show_page(0)

    @menus.button(
        "\N{BLACK RIGHT-POINTING TRIANGLE}", position=menus.First(10)
    )
    async def next(self, payload: discord.RawReactionActionEvent):
        await self.show_checked_page(self.current_page + 1)

    @menus.button(
        "\N{CROSS MARK}", position=menus.Last(0), skip_if=_can_send_custom
    )
    async def stop_pages_default(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        self.stop()

    @menus.button(
        "<:cross:631530205495689236>",
        position=menus.Last(0),
        skip_if=_can_not_send_custom,
    )
    async def stop_pages_custom(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        self.stop()


class Menus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def testmenu(self, ctx):
        await HelpMenu(
            source=MenuSource(
                [
                    MainHelp.first_page,
                    MainHelp.music_page,
                    MainHelp.general_page,
                    MainHelp.games_page,
                    MainHelp.images_page,
                    MainHelp.nsfw_page,
                    MainHelp.general_page,
                    MainHelp.utils_page,
                    MainHelp.general_page,
                ]
            ),
            delete_message_after=True,
            clear_reactions_after=True,
            timeout=180,
        ).start(ctx, wait=False)


def setup(bot):
    cog = Menus(bot)
    bot.add_cog(cog)
