# Future Imports
from __future__ import annotations

# Standard Library Imports
from collections import defaultdict, deque
from io import BytesIO
from typing import Literal

# Dependency Imports
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils import chat_formatting as cf
from redbot.vendored.discord.ext import menus
import discord


class MiniMsg:
    def __init__(self, msg: discord.Message):
        self.channel = msg.channel
        self.author = msg.author
        self.content = msg.content
        self.embed = msg.embeds[0] if msg.embeds else None
        # self.attachment = msg.attachments[0] if msg.attachments else None


# class EditMsg:
#     def __init__(self, before: discord.Message, after: discord.Message):
#         self.channel = before.channel
#         self.author = before.author
#         self.old_content = before.content
#         self.new_content = after.content
#         # self.embed = msg.embeds[0] if msg.embeds else None
#         # self.attachment = msg.attachments[0] if msg.attachments else None


class Sniper(commands.Cog):
    """
    Multi Snipe for fun and non-profit
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.cache = defaultdict(lambda: deque(maxlen=100))

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        self.cache[message.channel.id].append(MiniMsg(message))

    # @commands.Cog.listener()
    # async def on_message_edit(self, message):
    #     self.cache[message.channel.id].append(EditMsg(message))

    @commands.group(invoke_without_command=True)
    async def snipe(self, ctx: commands.Context, index: int = None):
        """
        Snipe a channel for fun and profit
        """
        if not self.cache[ctx.channel.id]:
            return await ctx.send("Nothing to snipe")
        if index is None:
            index = 1
        try:
            msg = self.cache[ctx.channel.id][-index]
            emb = discord.Embed(
                description=msg.content, color=await ctx.embed_color()
            )
            emb.set_author(
                name=msg.author,
                icon_url=msg.author.avatar.with_static_format("png").url,
            )
            await ctx.send(embed=emb)
        except IndexError:
            await ctx.send("Out of range")

    @snipe.command()
    async def embed(self, ctx):
        """
        Snipe past embeds in the channel
        """
        if embs := [
            msg.embed
            for msg in reversed(self.cache[ctx.channel.id])
            if msg.embed
        ]:
            await menus.MenuPages(
                source=EmbSource(embs, per_page=1),
                delete_message_after=True,
            ).start(ctx)
        else:
            await ctx.send("No embeds to snipe")

    @snipe.command()
    async def bulk(self, ctx):
        """
        List all snipes in the past
        """
        if self.cache[ctx.channel.id]:
            await menus.MenuPages(
                source=MsgSource(
                    [
                        msg
                        for msg in reversed(self.cache[ctx.channel.id])
                        if msg.content
                    ],
                    per_page=1,
                ),
                delete_message_after=True,
            ).start(ctx)
        else:
            await ctx.send("Nothing to snipe")

    # @snipe.command()
    # async def edit(self, ctx, index: int = None):
    #     """
    #     Snipe the last message edit
    #     """
    #     if not self.cache[ctx.channel.id]:
    #         return await ctx.send("Nothing to snipe")
    #     if index is None:
    #         index = 1
    #     try:
    #         msg = self.cache[ctx.channel.id][-index]
    #         emb = discord.Embed(description=msg.content, color=await ctx.embed_color())
    #         emb.set_author(name=msg.author, icon_url=msg.author.avatar.with_static_format("png").url)
    #         await ctx.send(embed=emb)
    #     except IndexError:
    #         await ctx.send("Out of range")

    async def red_delete_data_for_user(
        self, *, requester, user_id: int
    ) -> None:
        return


class MsgSource(menus.ListPageSource):
    async def format_page(self, menu, entry):
        emb = discord.Embed(description=entry.content)
        emb.set_author(name=entry.author, icon_url=entry.author.avatar.url)
        emb.set_footer(text=f"Page {menu.current_page+1}/{self._max_pages}")
        return emb


class EmbSource(menus.ListPageSource):
    async def format_page(self, menu, entry):
        return {
            "embed": entry,
            "content": f"Page {menu.current_page+1}/{self._max_pages}",
        }
