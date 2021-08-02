import asyncio
import typing
import json
import inspect
from dataclasses import dataclass
from typing import Union, Optional
import datetime

import discord
from discord.ext import commands


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
    interaction: discord.Interaction

    async def send(self, *args, **kwargs):
        if self.interaction.response.is_done():
            await self.interaction.followup.send(*args, **kwargs)
        else:
            await self.interaction.response.send_message(*args, **kwargs)


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

    def format_string(self, string, size):
        if len(string) > size:
            return string[: size - 3] + "..."
        return string

    async def parse_options(self, command):
        if isinstance(command, commands.Group):
            return [
                {
                    "name": command.name,
                    "description": self.format_string(
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
                required = False
            else:
                type = param.annotation
                required = param.default == inspect.Parameter.empty

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
                "description": self.format_string(
                    command.help or "no description", 100
                ),
                "options": await self.parse_options(command),
            }
            for command in self.bot.commands
            if command.qualified_name != "jishaku"
        ]
        with open("test.json", "w") as f:
            json.dump(cmds, f, indent=4)
        url = f"{discord.http.Route.BASE}/applications/{self.bot.user.id}/guilds/716596551887093873/commands"
        headers = {"Authorization": f"Bot {self.bot.http.token}"}
        async with self.bot.session.put(url, headers=headers, json=cmds) as resp:
            resp.raise_for_status()

    async def convert_param(self, ctx, option, param):
        value = option["value"]
        if param.annotation != inspect.Parameter.empty:
            value = await commands.run_converters(ctx, param.annotation, value, 0)
        return value

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
            interaction,
        )
        params = []
        kwargs = {}
        for name, param in command.clean_params.items():
            option = options.get(name)
            if not option:
                option = param.default
            else:
                option = await self.convert_param(ctx, option, param)
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
            await command(ctx, *params, **kwargs)
        except Exception as error:
            self.bot.dispatch("command_error".ctx, error)


def setup(bot):
    bot.add_cog(Slash(bot))
