import discord
from discord.ext.commands import cog

from helpers import constants, methods, misc
from discord.ext import commands


class HelpSelect(discord.ui.Select):
    def __init__(self, help_command, filtered_mapping, view):
        self.help_command = help_command
        super().__init__(
            placeholder="Select a category",
            options=[
                discord.components.SelectOption(
                    label=cog.qualified_name,
                    value=cog.qualified_name,
                    description=methods.format_string(cog.description, 47),
                )
                for cog in filtered_mapping
                if cog
            ] + [
                discord.components.SelectOption(
                    label="View the tutorial",
                    value="tutorial",
                    description="Get a tutorial of the bot"
                )
            ],
        )

    async def callback(self, interaction):
        if self.values[0] == "tutorial":
            await self.help_command.current_message.delete()
            return await self.help_command.context.bot.get_command("tutorial")(self.help_command.context)
        selected = self.help_command.context.bot.get_cog(self.values[0])
        await self.help_command.send_cog_help(selected, view=self.view)


class CustomHelp(commands.HelpCommand):
    current_message = None

    def get_command_signature(self, command):
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            fmt = f"{command.name}"
            if parent:
                fmt = f"{parent} {fmt}"
            alias = fmt
        else:
            alias = command.name if not parent else f"{parent} {command.name}"
        return f"{alias} {command.signature}"

    async def send_bot_help(self, mapping):
        embed = constants.Embed(
            title="Pokeland Help!",
            description=f"Use `{self.context.prefix}help <command/category>` for more infomation",
        )
        embed.set_thumbnail(url=self.context.me.avatar.url)
        filtered = {}
        for cog, commands in mapping.items():
            commands = await self.filter_commands(commands, sort=True)
            if not commands:
                continue
            filtered[cog] = commands
            if cog:
                name = cog.qualified_name
                value = cog.description
            else:
                name = "No Category"
                value = "Commands with no category"
            embed.add_field(
                name=name,
                value=f"{value}\n{' '.join(f'`{command.qualified_name}`' for command in commands[:25])}",
                inline=False,
            )

        view = misc.RestrictedView(owner=self.context.author)
        view.add_item(HelpSelect(self, filtered, view))
        destination = self.get_destination()
        self.current_message = await destination.send(embed=embed, view=view)

    def add_commands_to_embed(self, embed, cmds):
        for cmd in cmds:
            help = cmd.help or "No help provided..."
            if isinstance(cmd, commands.Group):
                help = f"[Group] {help}"
            embed.add_field(
                name=self.get_command_signature(cmd), value=help, inline=False
            )

    async def send_cog_help(self, cog, view=None):
        embed = constants.Embed(title=f"{cog.qualified_name} Help!".title())
        embed.set_thumbnail(url=self.context.me.avatar.url)
        self.add_commands_to_embed(
            embed, await self.filter_commands(cog.get_commands())
        )
        if self.current_message:
            await self.current_message.edit(embed=embed, view=view)
        else:
            destination = self.get_destination()
            await destination.send(embed=embed)

    async def send_command_help(self, command):
        embed = constants.Embed(
            title=self.get_command_signature(command),
            description=command.help or "No help provided...",
        )
        if command.cog:
            category = command.cog.qualified_name
        else:
            category = "None"
        embed.add_field(name="Category", value=category)

        if command.aliases:
            embed.add_field(name="Aliases", value=" | ".join(command.aliases))

        try:
            can_run = "Yes" if await command.can_run(self.context) else "No"
        except:
            can_run = "No"
        embed.add_field(name="Runnable?", value=can_run)

        if hasattr(command, "_buckets") and command._buckets._cooldown:
            embed.add_field(
                name="Cooldown",
                value=f"{command._buckets._cooldown.rate} per {int(command._buckets._cooldown.per)} seconds",
            )
        destination = self.get_destination()
        await destination.send(embed=embed)

    async def send_group_help(self, group):
        cmds = await self.filter_commands(group.commands)
        if not cmds:
            return await self.send_command_help(group)
        embed = constants.Embed(
            title=self.get_command_signature(group),
            description=f"{group.help or 'No help provided...'}\nUse `{self.context.prefix}help <command>` for more infomation",
        )
        self.add_commands_to_embed(embed, cmds)
        destination = self.get_destination()
        await destination.send(embed=embed)


def setup(bot):
    bot.help_command = CustomHelp()


def teardown(bot):
    bot.help_command = commands.DefaultHelpCommand()
