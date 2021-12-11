# Future Imports
from __future__ import annotations

# Standard Library Imports
from typing import Set

# Dependency Imports
import discord

# Music Imports
from ....utils import timed_alru_cache
from .abc import CacheBase


class BotConfigManager(CacheBase):
    __slots__ = (
        "_config",
        "bot",
        "enable_cache",
        "config_cache",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @timed_alru_cache(
        seconds=60
    )  # 60 second cache, this is so that multiple back to back calls only call config once
    async def get_admin_roles(self, guild: discord.Guild) -> Set[discord.Role]:
        if guild is None:
            return set()
        ret: Set[int]
        gid: int = guild.id
        ret = await self.bot._config.guild_from_id(gid).admin_role()
        return {y for r in ret if (y := guild.get_role(r)) in guild.roles}

    @timed_alru_cache(
        seconds=60
    )  # 60 second cache, this is so that multiple back to back calls only call config once
    async def get_mod_roles(self, guild: discord.Guild) -> Set[discord.Role]:
        if guild is None:
            return set()
        ret: Set[int]
        gid: int = guild.id
        ret = await self.bot._config.guild_from_id(gid).mod_role()
        return {y for r in ret if (y := guild.get_role(r)) in guild.roles}

    async def get_admin_members(
        self, guild: discord.Guild
    ) -> Set[discord.Member]:
        if guild is None:
            return set()
        members = {
            member
            for m in self.bot.owner_ids
            if (member := guild.get_member(m))
        }
        members |= {
            member
            for role in await self.get_admin_roles(guild)
            for member in role.members
        }
        return members

    async def get_admin_member_ids(self, guild: discord.Guild) -> Set[int]:
        if guild is None:
            return set()
        member_ids = {*self.bot.owner_ids}
        member_ids |= {
            member.id
            for role in await self.get_admin_roles(guild)
            for member in role.members
        }
        return member_ids

    async def get_mod_members(
        self, guild: discord.Guild
    ) -> Set[discord.Member]:
        if guild is None:
            return set()
        members = {
            member
            for m in self.bot.owner_ids
            if (member := guild.get_member(m))
        }
        members |= {
            member
            for role in await self.get_mod_roles(guild)
            for member in role.members
        }
        members |= {
            member
            for role in await self.get_admin_roles(guild)
            for member in role.members
        }
        return members

    async def get_mod_member_ids(self, guild: discord.Guild) -> Set[int]:
        if guild is None:
            return set()
        member_ids = {*self.bot.owner_ids}
        member_ids |= {
            member.id
            for role in await self.get_mod_roles(guild)
            for member in role.members
        }
        member_ids |= {
            member.id
            for role in await self.get_admin_roles(guild)
            for member in role.members
        }
        return member_ids

    async def member_is_admin_or_higher(
        self, guild: discord.Guild, member: discord.Member
    ) -> bool:
        return member.id in await self.get_admin_member_ids(guild)

    async def member_is_mod_or_higher(
        self, guild: discord.Guild, member: discord.Member
    ) -> bool:

        return member.id in await self.get_mod_member_ids(guild)

    async def get_context_value(
        self,
        guild: discord.Guild,
        member: discord.Member,
        *,
        mod: bool,
        admin: bool,
    ) -> bool:
        if guild is None:
            return False
        if mod:
            return await self.member_is_mod_or_higher(guild, member)
        elif admin:
            return await self.member_is_admin_or_higher(guild, member)
        else:
            return member.id in self.bot.owner_ids

    def reset_globals(self) -> None:
        pass
