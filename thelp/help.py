# Future Imports
from __future__ import annotations

# Standard Library Imports
import asyncio
import math

# Dependency Imports
from discord.interactions import Interaction
from discord.ui import Button, button, View
from redbot.core import commands
from redbot.core.i18n import cog_i18n, Translator
import discord

_ = Translator("THelp", __file__)


@cog_i18n(_)
class CogMenu(View):
    def __init__(
        self,
        *,
        title: str,
        description: str,
        bot,
        color: int,
        footer: str,
        per_page: int = 5,
    ) -> None:
        self.title = title
        self.description = description
        self.bot = bot
        self.color = color
        self.footer = footer
        self.per_page = per_page
        self.page = 1
        self.message: discord.Message = None
        self.allowed_user: discord.User = None

        super().__init__(timeout=60.0)

    @property
    def pages(self) -> int:
        return math.ceil(len(self.description) / self.per_page)

    def embed(self, desc: str) -> discord.Embed:
        e = discord.Embed(
            title=self.title, color=self.color, description="\n".join(desc)
        )
        e.set_author(
            name=self.bot.user,
            icon_url=self.bot.user.display_avatar.url,
        )
        e.set_footer(
            text=f"{self.footer} | Page {self.page}/{self.pages}",
            icon_url=self.bot.user.display_avatar.url,
        )
        return e

    def should_process(self) -> bool:
        return len(self.description) > self.per_page

    def cleanup(self) -> None:
        asyncio.create_task(self.message.delete())

    async def on_timeout(self) -> None:
        self.cleanup()

    async def start(self, ctx: commands.Context) -> None:
        self.allowed_user = ctx.author
        e = self.embed(self.description[0 : self.per_page])

        if self.should_process():
            self.message = await ctx.send(embed=e, view=self)
        else:
            self.message = await ctx.send(embed=e)

    async def update(self) -> None:
        start = (self.page - 1) * self.per_page
        end = self.page * self.per_page
        items = self.description[start:end]
        e = self.embed(items)
        await self.message.edit(embed=e)

    async def interaction_check(
        self, interaction: discord.Interaction
    ) -> bool:
        if self.allowed_user.id == interaction.user.id:
            return True
        else:
            asyncio.create_task(
                interaction.response.send_message(
                    _("This command was not initiated by you."), ephemeral=True
                )
            )
            return False

    @button(
        label="Previous",
        style=discord.ButtonStyle.blurple,
        emoji="\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f",
    )
    async def on_previous_page(
        self, button: Button, interaction: Interaction
    ) -> None:
        if self.page != 1:
            self.page -= 1
            await self.update()

    @button(
        label="Stop",
        style=discord.ButtonStyle.red,
        emoji="\N{BLACK SQUARE FOR STOP}\ufe0f",
    )
    async def on_stop(self, button: Button, interaction: Interaction) -> None:
        self.cleanup()
        self.stop()

    @button(
        label="Next",
        style=discord.ButtonStyle.blurple,
        emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f",
    )
    async def on_next_page(
        self, button: Button, interaction: Interaction
    ) -> None:
        if len(self.description) >= (self.page * self.per_page):
            self.page += 1
            await self.update()


class SubcommandMenu(View):
    def __init__(
        self,
        *,
        cmds: list[commands.Command],
        title: str,
        description: str,
        bot,
        color: int,
        per_page: int = 5,
    ) -> None:
        self.cmds = cmds
        self.title = title
        self.description = description
        self.bot = bot
        self.color = color
        self.per_page = per_page
        self.page = 1
        self.group_emoji = "💠"
        self.command_emoji = "🔷"

        self.message: discord.Message = None
        self.ctx: commands.Context = None

        super().__init__(timeout=60.0)

    @property
    def pages(self) -> int:
        return math.ceil(len(self.cmds) / self.per_page)

    def embed(self, cmds: list[commands.Command]) -> discord.Embed:
        e = discord.Embed(
            title=self.title, color=self.color, description=self.description
        )
        e.set_author(
            name=self.bot.user,
            icon_url=self.bot.user.display_avatar.url,
        )
        e.add_field(
            name=_("Subcommands"),
            value="\n".join(
                [
                    f"{self.group_emoji if isinstance(c, commands.Group) else self.command_emoji}"
                    f" `{self.ctx.prefix}{c.qualified_name}` - {_(c.brief)}"
                    for c in cmds
                ]
            ),
        )
        if self.should_process():
            e.set_footer(
                icon_url=self.bot.user.display_avatar.url,
                text=_(
                    "Click on the buttons to see more subcommands. | Page"
                    " {start}/{end}"
                ).format(start=self.page, end=self.pages),
            )
        return e

    def should_process(self) -> bool:
        return len(self.cmds) > self.per_page

    def cleanup(self) -> None:
        asyncio.create_task(self.message.delete())

    async def on_timeout(self) -> None:
        self.cleanup()

    async def start(self, ctx: commands.Context) -> None:
        self.ctx = ctx
        e = self.embed(self.cmds[0 : self.per_page])

        if self.should_process():
            self.message = await ctx.send(embed=e, view=self)
        else:
            self.message = await ctx.send(embed=e)

    async def update(self) -> None:
        start = (self.page - 1) * self.per_page
        end = self.page * self.per_page
        items = self.cmds[start:end]
        e = self.embed(items)
        await self.message.edit(embed=e)

    async def interaction_check(
        self, interaction: discord.Interaction
    ) -> bool:
        if self.ctx.author.id == interaction.user.id:
            return True
        else:
            asyncio.create_task(
                interaction.response.send_message(
                    _("This command was not initiated by you."), ephemeral=True
                )
            )
            return False

    @button(
        label="Previous",
        style=discord.ButtonStyle.blurple,
        emoji="\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f",
    )
    async def on_previous_page(
        self, button: Button, interaction: Interaction
    ) -> None:
        if self.page != 1:
            self.page -= 1
            await self.update()

    @button(
        label="Stop",
        style=discord.ButtonStyle.red,
        emoji="\N{BLACK SQUARE FOR STOP}\ufe0f",
    )
    async def on_stop(self, button: Button, interaction: Interaction) -> None:
        self.cleanup()
        self.stop()

    @button(
        label="Next",
        style=discord.ButtonStyle.blurple,
        emoji="\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f",
    )
    async def on_next_page(
        self, button: Button, interaction: Interaction
    ) -> None:
        if len(self.cmds) >= (self.page * self.per_page):
            self.page += 1
            await self.update()


class IdleHelp(commands.HelpCommand):
    def __init__(self, *args, **kwargs):
        kwargs["command_attrs"] = {
            "brief": _("Views the help on a topic."),
            "help": _(
                """Views the help on a topic.
            The topic may either be a command name or a module name.
            Command names are always preferred, so for example, `{prefix}help adventure`
            will show the help on the command, not the module.
            To view the help on a module explicitely, use `{prefix}help module [name]`"""
            ),
        }

        super().__init__(*args, **kwargs)
        self.verify_checks = False
        self.color = None
        self.gm_exts = {"GameMaster"}
        self.owner_exts = {"Owner"}
        self.group_emoji = "💠"
        self.command_emoji = "🔷"

    async def command_callback(self, ctx, *, command=None):
        await self.prepare_help_command(ctx, command)
        bot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        PREFER_COG = False
        if command.lower().startswith(("module ", "module:")):
            command = command[7:]
            PREFER_COG = True

        if PREFER_COG:
            if command.lower() == "gamemaster":
                command = "GameMaster"
            else:
                command = command.title()
            cog = bot.get_cog(command)
            if cog is not None:
                return await self.send_cog_help(cog)

        maybe_coro = discord.utils.maybe_coroutine

        keys = command.split(" ")
        cmd = bot.all_commands.get(keys[0])
        if cmd is None:
            cog = bot.get_cog(command.title())
            if cog is not None:
                return await self.send_cog_help(cog)

            string = await maybe_coro(
                self.command_not_found, self.remove_mentions(keys[0])
            )
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)
            except AttributeError:
                string = await maybe_coro(
                    self.subcommand_not_found, cmd, self.remove_mentions(key)
                )
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(
                        self.subcommand_not_found,
                        cmd,
                        self.remove_mentions(key),
                    )
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, commands.Group):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)

    async def send_bot_help(self, mapping):
        e = discord.Embed(
            title=_(
                "IdleRPG Help {version}",
            ).format(version=self.context.bot.version),
            color=self.context.bot.config.game.primary_colour,
            url="https://idlerpg.xyz/",
        )
        e.set_author(
            name=self.context.bot.user,
            icon_url=self.context.bot.user.display_avatar.url,
        )
        e.set_image(
            url="https://media.discordapp.net/attachments/460568954968997890/711740723715637288/idle_banner.png"
        )
        e.description = _(
            "**Welcome to the IdleRPG help.**\nCheck out our tutorial!\n-"
            " https://idlerpg.xyz/tutorial/\nAre you stuck? Ask for help in the support"
            " server!\n- https://support.idlerpg.xyz/\nDo you need personal help?\n-"
            " Contact our support team using `{prefix}helpme`.\nWould you like to"
            " invite me to your server?\n- https://invite.idlerpg.xyz/\n*See"
            " `{prefix}help [command]` and `{prefix}help module [module]` for more"
            " info*"
        ).format(prefix=self.context.prefix)

        allowed = []
        for cog in sorted(
            mapping.keys(), key=lambda x: x.qualified_name if x else ""
        ):
            if cog is None:
                continue
            if (
                self.context.author.id
                not in self.context.bot.config.game.game_masters
                and cog.qualified_name in self.gm_exts
            ):
                continue
            if (
                self.context.author.id not in self.context.bot.owner_ids
                and cog.qualified_name in self.owner_exts
            ):
                continue
            if (
                cog.qualified_name not in self.gm_exts
                and len([c for c in cog.get_commands() if not c.hidden]) == 0
            ):
                continue
            allowed.append(cog.qualified_name)
        cogs = [allowed[x : x + 3] for x in range(0, len(allowed), 3)]
        length_list = [len(element) for row in cogs for element in row]
        column_width = max(length_list)
        rows = []
        for row in cogs:
            rows.append(
                "".join(element.ljust(column_width + 2) for element in row)
            )
        e.add_field(
            name=_("Modules"), value="```{}```".format("\n".join(rows))
        )

        await self.context.send(embed=e)

    async def send_cog_help(self, cog):
        if (cog.qualified_name in self.gm_exts) and (
            self.context.author.id
            not in self.context.bot.config.game.game_masters
        ):
            if self.context.author.id in self.context.bot.owner_ids:
                pass  # owners don't have restrictions
            else:
                return await self.context.send(
                    _("You do not have access to these commands!")
                )
        if (cog.qualified_name in self.owner_exts) and (
            self.context.author.id not in self.context.bot.owner_ids
        ):
            return await self.context.send(
                _("You do not have access to these commands!")
            )

        menu = CogMenu(
            title=(
                f"[{cog.qualified_name.upper()}] {len(set(cog.walk_commands()))}"
                " commands"
            ),
            bot=self.context.bot,
            color=self.context.bot.config.game.primary_colour,
            description=[
                f"{self.group_emoji if isinstance(c, commands.Group) else self.command_emoji}"
                f" `{self.context.clean_prefix}{c.qualified_name} {c.signature}` - {_(c.brief)}"
                for c in cog.get_commands()
            ],
            footer=_(
                "See '{prefix}help <command>' for more detailed info"
            ).format(prefix=self.context.prefix),
        )

        await menu.start(self.context)

    async def send_command_help(self, command):
        if command.cog:
            if (command.cog.qualified_name in self.gm_exts) and (
                self.context.author.id
                not in self.context.bot.config.game.game_masters
            ):
                if self.context.author.id in self.context.bot.owner_ids:
                    pass  # owners don't have restrictions
                else:
                    return await self.context.send(
                        _("You do not have access to this command!")
                    )
            if (command.cog.qualified_name in self.owner_exts) and (
                self.context.author.id not in self.context.bot.owner_ids
            ):
                return await self.context.send(
                    _("You do not have access to this command!")
                )

        e = discord.Embed(
            title=(
                f"[{command.cog.qualified_name.upper()}] {command.qualified_name}"
                f" {command.signature}"
            ),
            colour=self.context.bot.config.game.primary_colour,
            description=_(command.help).format(prefix=self.context.prefix),
        )
        e.set_author(
            name=self.context.bot.user,
            icon_url=self.context.bot.user.display_avatar.url,
        )

        if command.aliases:
            e.add_field(
                name=_("Aliases"),
                value="`{}`".format("`, `".join(command.aliases)),
            )
        await self.context.send(embed=e)

    async def send_group_help(self, group):
        if group.cog:
            if (
                self.context.author.id
                not in self.context.bot.config.game.game_masters
                and group.cog.qualified_name in self.gm_exts
            ):
                return await self.context.send(
                    _("You do not have access to this command!")
                )
            if (
                self.context.author.id not in self.context.bot.owner_ids
                and group.cog.qualified_name in self.owner_exts
            ):
                return await self.context.send(
                    _("You do not have access to this command!")
                )

        menu = SubcommandMenu(
            title=(
                f"[{group.cog.qualified_name.upper()}] {group.qualified_name}"
                f" {group.signature}"
            ),
            bot=self.context.bot,
            color=self.context.bot.config.game.primary_colour,
            description=_(group.help).format(prefix=self.context.prefix),
            cmds=list(group.commands),
        )
        await menu.start(self.context)


def setup(bot):
    bot.remove_command("help")
    bot.help_command = IdleHelp()
