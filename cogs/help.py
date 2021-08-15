import discord
from discord.ext.commands import cog

from helpers import constants, methods, misc
from discord.ext import commands, menus
from discord.ext.menus.views import ViewMenuPages

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
            ]
            + [
                discord.components.SelectOption(
                    label="View the tutorial",
                    value="tutorial",
                    description="Get a tutorial of the bot",
                )
            ],
        )

    async def callback(self, interaction):
        if self.values[0] == "tutorial":
            await self.help_command.current_message.delete()
            return await self.help_command.context.bot.get_command("tutorial")(
                self.help_command.context
            )
        selected = self.help_command.context.bot.get_cog(self.values[0])
        await self.help_command.send_cog_help(selected, view=self.view)

class FormatCogHelp(menus.ListPageSource):
    def __init__(self, entries, ctx, cog, per_page = 5):
        super().__init__(
            entries=entries,
            per_page=per_page
        )
        self.ctx = ctx
        self.cog = cog
    
    async def format_page(self, menu, entry):
        embed = constants.Embed(
            title = f"{self.cog.qualified_name} Help!",
            description=f"Use `{self.ctx.prefix}help <command/category>` for more information."
        )

        embed.set_thumbnail(url=self.ctx.me.avatar.url)

        for command in entry:
            name = f"{command.name} {command.signature}"
            value = f"{command.help or 'No help given'}"

            if isinstance(command, commands.Group):
                name = f"[Group] {name}"

            embed.add_field(
                name=name,
                value= value,
                inline=False
            )
        
        return embed

class FormatGroupHelp(menus.ListPageSource):
    def __init__(self, entries, ctx, group, per_page = 5):
        super().__init__(
            entries=entries,
            per_page=per_page
        )
        self.ctx = ctx
        self.group = group
    
    async def format_page(self, menu: menus.Menu, entries: List[commands.Command]) -> discord.Embed:
        embed = constants.Embed(
            title = f"{self.group.qualified_name} Help!",
            description=f"Use `{self.ctx.prefix}help <command/category>` for more information."
        )

        embed.set_thumbnail(url=self.ctx.me.avatar.url)

        for command in entries:
            help = command.help
        
            if isinstance(command, commands.Group):
                help = f"[Group] {help}"

            embed.add_field(
                name=f"{command} {command.signature}",
                value=help,
                inline=False
            )

        return embed

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

    async def send_cog_help(self, cog, view=None):
        commands = await self.filter_commands(cog.get_commands())

        if not commands:
            return
        
        source = FormatCogHelp(commands, self.context, cog)

        await ViewMenuPages(source=source).start(self.context)

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
        
        permissions = []
        for check in command.checks:
            print(check.__qualname__)
            if check.__qualname__.partition(".")[0] in ("has_permissions", "has_guild_permissions"):
                perms = await methods.get_permissions(check)
                permissions.extend(perm.replace("_", " ").replace("guild", "server").title() for perm in perms.keys())
        if permissions:
            embed.add_field(
                name="Required permissions",
                value=methods.bullet_list(permissions)
            )


        destination = self.get_destination()
        await destination.send(embed=embed)

    async def send_group_help(self, group):
        cmds = await self.filter_commands(group.commands)
        if not cmds:
            return await self.send_command_help(group)
        
        source = FormatGroupHelp(cmds, self.context, group)

        await ViewMenuPages(source=source).start(self.context)


def setup(bot):
    bot.help_command = CustomHelp()


def teardown(bot):
    bot.help_command = commands.DefaultHelpCommand()
