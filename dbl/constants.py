# Future Imports
from __future__ import annotations

# Standard Library Imports
from typing import Union

# Dependency Imports
from discord import embeds
import aiohttp
import discord


def get_user(user: Union[int, discord.Member], ctx=None):
    if isinstance(user, int):
        user = ctx.bot.get_user(user)
    return user


class Embed(embeds.Embed):
    def __init__(self, **kwargs):
        if "colour" not in kwargs:
            kwargs["colour"] = discord.Color.random()

        super().__init__(**kwargs)


class ErrorEmbed(embeds.Embed):
    def __init__(self, **kwargs):
        if "colour" not in kwargs:
            kwargs["colour"] = discord.Color.red()

        super().__init__(**kwargs)


def votedTopgg(self, ctx):
    a = aiohttp.ClientSession.get(
        url=f"https://top.gg/api/bots/{ctx.bot.user.id}/check",
        params={"userId": ctx.message.author.id},
    )
    try:
        a_list = True if a.json().get("voted") >= 1 else False
    except aiohttp.ClientSession.exceptions.ConnectionError:
        a_list = True
    except:
        a_list = False
    return a_list


def votedbotsfordiscord(self, ctx):
    c = aiohttp.ClientSession.get(
        url=f"https://discords.com/bots/api/bot/{ctx.bot.user.id}/votes",
        headers={"Authorization": bfd_token},
    )
    try:
        c_list = (
            True
            if str(ctx.message.author.id) in c.json().get("hasVoted24", False)
            else False
        )
    except aiohttp.ClientSession.exceptions.ConnectionError:
        c_list = True
    except:
        c_list = False
    return c_list


def generatedailyembed(self, ctx, *argv):
    list_dict = {
        "top.gg": "https://top.gg/images/dblnew.png",
        "botsfordiscord": "https://botsfordiscord.com/img/favicons/apple-touch-icon-57x57.png",
    }
    site_dict = {
        "top.gg": f"https://top.gg/bot/{ctx.bot.user.id}",
        "botsfordiscord": f"https://botsfordiscord.com/bot/{ctx.bot.user.id}",
    }
    if isinstance(argv[0], str):
        e = ErrorEmbed(
            title="You Need To Vote!",
            description=f"""You didn\'t vote for me in **[{argv[0].capitalize()}]({site_dict[argv[0].lower()]})** :angry:. The `{ctx.prefix}{ctx.command.name}` **requires**  you to vote.
            [Click Here]({site_dict[argv[0].lower()]}) to __vote__ for me in **{argv[0].capitalize()}** :wink:.
            """,
            timestamp=ctx.message.created_at,
        )
        e.set_thumbnail(url=list_dict[argv[0].lower()])
        e.set_author(
            name=ctx.message.author,
            url=site_dict[argv[0].lower()],
            icon_url=ctx.message.author.avatar.with_static_format("png").url,
        )
        e.set_footer(
            text=f"Vote for us in {argv[0].lower()} and enjoy free credits (and more coming soon!)"
        )
    else:
        join_string = "\n・"
        e = ErrorEmbed(
            title="You Need To Vote!",
            description=f'You need to **vote for me** in the **following botlists** :smile: :\n・{join_string.join(list(f"**[{i.capitalize()}]({site_dict[i.lower()]})**" for i in argv[0]))}',
            timestamp=ctx.message.created_at,
        )
        e.set_author(
            name=ctx.message.author,
            icon_url=ctx.message.author.avatar.with_static_format("png").url,
        )
        e.set_thumbnail(
            url=ctx.message.author.avatar.with_static_format("png").url
        )
        e.set_footer(
            text="Vote for us in the above mentioned botlists and then enjoy free credits."
        )
    return e
