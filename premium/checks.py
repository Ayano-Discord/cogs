# Future Imports
from __future__ import annotations

# Dependency Imports
import discord


def is_premium(ctx):
    sguild = ctx.bot.get_guild(852094131047104593)
    orole = sguild.get_role(852094131231522819)
    bguild = ctx.bot.get_guild(852094131047104593)
    return (
        ctx.author.id in bguild.premium_subscribers
        or ctx.bot.owner_ids
        or orole
    )


def is_bot_staff(ctx):
    sguild = ctx.bot.get_guild(852094131047104593)
    orole = sguild.get_role(852094131231522819)
    srole = sguild.get_role(852094131231522818)
    return ctx.author.id in ctx.bot.owner_ids or orole or srole


def premium_tier_checker(ctx):
    # guild = ctx.bot.get_guild(852094131047104593)
    for role in ctx.author.roles:
        if role.id == 852094131231522819:
            return 5
        elif role.id == 869063620829528115:
            return 4
        elif role.id == 852094131231522816:
            return 3
        elif role.id == 852094131047104597:
            return 2
        elif role.id == 873788122926813245:
            return 1
        else:
            return 0


#
