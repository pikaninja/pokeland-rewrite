import asyncio
import typing
import json
import inspect
from dataclasses import dataclass
from helpers import methods
from typing import Union, Optional
import datetime


import discord
from discord.ext import commands


@dataclass
class FakeUser:
    name: str
    discrim: str
    id: str

    def __str__(self):
        return f"{self.name}#{self.discrim}"

    @property
    def mention(self):
        return f"<@{self.id}>"


@dataclass
class FalseMessage:
    content: str
    created_at: datetime.datetime


@dataclass
class SlashContext:
    bot: commands.Bot
    author: Union[discord.Member, discord.User]
    channel: Union[discord.TextChannel, discord.DMChannel]
    guild: discord.Guild
    message: FalseMessage
    command: commands.Command
    interaction: discord.Interaction
    current_parameter: int = 0
    prefix: str = "/"

    @property
    def cog(self):
        return self.command.cog

    async def send(self, *args, **kwargs):
        if self.interaction.response.is_done():
            return await self.interaction.followup.send(*args, **kwargs)
        else:
            await self.interaction.response.send_message(*args, **kwargs)
            return await self.interaction.original_message()


class Flags:
    def __getattr__(self, item):
        return self.__dict__.get(item, None)


class Slash(commands.Cog):
    """The cog for handling slash command"""

    TYPES = {
        str: 3,
        int: 4,
        bool: 5,
        discord.User: 6,
        discord.Member: 6,
        discord.TextChannel: 7,
        discord.Role: 8,
    }
    DISCORD_TYPES = [
        str,
        int,
        bool,
        discord.User,
        discord.Member,
        discord.TextChannel,
        discord.Role,
    ]

    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.build_slash_commands())

    async def parse_options(self, command):
        if isinstance(command, commands.Group):
            return [
                {
                    "name": command.name,
                    "description": methods.format_string(
                        command.help or "no decription", 100
                    ),
                    "type": 1,
                    "options": await self.parse_options(command),
                }
                for command in command.commands
            ]

        signature = command.clean_params
        options = []
        for name, param in signature.items():
            if getattr(param.annotation, "__origin__", None) is typing.Union:
                type = param.annotation.__args__[0]
                if param.annotation.__args__[1] is None:
                    required = False
                else:
                    required = True
            else:
                type = param.annotation
                required = param.default == inspect.Parameter.empty

            if self.is_flag(param.annotation):
                for name, flag in param.annotation.get_flags().items():
                    if flag.default != ...:
                        required = False
                    else:
                        required = True
                    type = flag.annotation
                    if type in self.DISCORD_TYPES:
                        type = self.TYPES[type]
                    else:
                        type = self.TYPES[str]
                    options.append(
                        {
                            "name": name,
                            "description": name,
                            "type": type,
                            "required": required,
                        }
                    )
                continue

            if type in self.DISCORD_TYPES:
                options.append(
                    {
                        "name": name,
                        "description": name,
                        "type": self.TYPES[type],
                        "required": required,
                    }
                )
            else:
                options.append(
                    {
                        "name": name,
                        "description": name,
                        "type": self.TYPES[str],
                        "required": required,
                    }
                )
        return options

    async def build_slash_commands(self):
        await self.bot.wait_until_ready()
        cmds = [
            {
                "name": command.name,
                "description": methods.format_string(
                    command.help or "no description", 100
                ),
                "options": await self.parse_options(command),
            }
            for command in self.bot.commands
            if command.qualified_name != "jishaku"
        ]
        if self.bot.config.debug:
            with open("test.json", "w") as f:
                json.dump(cmds, f, indent=4)
        url = f"{discord.http.Route.BASE}/applications/{self.bot.user.id}/commands"
        headers = {"Authorization": f"Bot {self.bot.http.token}"}
        async with self.bot.session.put(url, headers=headers, json=cmds) as resp:
            resp.raise_for_status()

    async def real_convert(self, ctx, option, param):
        if option["type"] == 6:
            data = ctx.interaction.data["resolved"]["users"][option["value"]]
            return FakeUser(data["username"], data["discriminator"], int(data["id"]))
        if param.annotation == inspect.Parameter.empty:
            return option["value"]
        return await commands.run_converters(ctx, param.annotation, option["value"], 0)

    async def convert_param(self, ctx, option, param, options):
        if param.annotation != inspect.Parameter.empty:
            if self.is_flag(param.annotation):
                flag = Flags()
                for name, option in options.items():
                    if name not in ctx.command.clean_params.keys():
                        type = param.annotation.get_flags()[name].annotation
                        setattr(flag, name, await self.real_convert(ctx, option, param))
                return flag
            value = await self.real_convert(ctx, option, param)
            return value
        return option["value"]

    def is_flag(self, annotation):
        return (
            inspect.isclass(annotation)
            and issubclass(annotation, commands.FlagConverter)
        ) or isinstance(annotation, commands.FlagConverter)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Bad idea test"""
        if interaction.type != discord.InteractionType.application_command:
            return

        command = interaction.data["name"]
        options = interaction.data.get("options", [])
        for option in options:
            if option["type"] in {1, 2}:
                command += f" {option['name']}"
                options = option.get("options", [])
                break
        command = self.bot.get_command(command)

        if not command:
            return

        options = {option["name"]: option for option in options}

        params = " ".join(
            f"{name}: {str(option['value'])}" for name, option in options.items()
        )
        content = f"/{command} {params}"
        message = FalseMessage(content, discord.utils.utcnow())
        ctx = SlashContext(
            self.bot,
            interaction.user,
            interaction.channel,
            interaction.guild,
            message,
            command,
            interaction,
        )
        params = []
        kwargs = {}
        for name, param in command.clean_params.items():
            option = options.get(name)
            if (not option) and not self.is_flag(param.annotation):
                option = param.default
            else:
                option = await self.convert_param(ctx, option, param, options)
            if param.kind == inspect.Parameter.KEYWORD_ONLY:
                kwargs[name] = option
            else:
                params.append(option)

        async def fallback():
            await asyncio.sleep(1)
            if interaction.response.is_done():
                return
            await interaction.response.send_message(
                f"You invoked the command {command}."
            )

        self.bot.loop.create_task(fallback())
        try:
            if await command.can_run(ctx):
                await command(ctx, *params, **kwargs)
            else:
                raise commands.CheckFailure()
        except Exception as error:
            self.bot.dispatch("command_error", ctx, error)


def setup(bot):
    bot.add_cog(Slash(bot))
