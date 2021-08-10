import io
import copy
import time
import discord
import pathlib
import textwrap
import traceback

from typing import Union
from contextlib import redirect_stdout

from helpers import misc
from discord.ext import commands
from prettytable import PrettyTable
from jishaku.codeblocks import codeblock_converter


class Admin(commands.Cog):
    """Commands for bot administration"""
    def __init__(self, bot):
        if not hasattr(bot, "extension_checked_at"):
            bot.extension_checked_at = time.time()

    @commands.group(case_insensitive=True)
    @commands.is_owner()
    async def dev(self, ctx):
        """The group command for development commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @dev.command()
    @commands.is_owner()
    async def random_spawn(self, ctx):
        """Spawn a random pokemon"""
        await ctx.bot.get_cog("Spawning").spawn_pokemon(ctx.channel)

    @dev.command()
    @commands.is_owner()
    async def spawn(self, ctx, *, pokemon):
        """Spawn a specific pokemon"""
        await ctx.bot.get_cog("Spawning").spawn_pokemon(ctx.channel, pokemon)

    @dev.command()
    @commands.is_owner()
    async def give_pokemon(self, ctx, target: discord.Member, *, pokemon):
        """Add pokemon to a user"""
        shiny = False
        if pokemon.startswith("shiny"):
            shiny = True
            pokemon = pokemon.replace("shiny ", "")
        pokemon = ctx.bot.data.get_species_by_name(pokemon)
        if not pokemon:
            return await ctx.send("invalid pokemon")

        await ctx.bot.db.insert_pokemon(target, pokemon["species_id"], shiny=shiny)
        await ctx.message.add_reaction("\U00002705")

    @dev.command()
    @commands.is_owner()
    async def suspend(self, ctx, target: discord.User):
        """Suspend a user from the bot"""
        await ctx.bot.connection.execute("UPDATE users SET disabled=true WHERE id = $1", target.id)
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @dev.command()
    @commands.is_owner()
    async def unsuspend(self, ctx, target: discord.User):
        """Unsuspend a user from the bot"""
        await ctx.bot.connection.execute("UPDATE users SET disabled=false WHERE id = $1", target.id)
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @dev.command()
    @commands.is_owner()
    async def sudo(self, ctx, target: Union[discord.Member, discord.User], *, command):
        """Sudo the command as another user"""
        message = copy.copy(ctx.message)
        message.author = target
        message.content = f"{ctx.prefix}{command}"

        context = await ctx.bot.get_context(message)
        await ctx.bot.invoke(context)

    @dev.command()
    @commands.is_owner()
    async def bypass(self, ctx, *, command):
        """Bypass the checks for a command"""
        message = copy.copy(ctx.message)
        message.content = f"{ctx.prefix}{command}"

        context = await ctx.bot.get_context(message)
        await context.reinvoke()

    @dev.command()
    @commands.is_owner()
    async def sql(self, ctx, *, code):
        """Run an sql query"""
        query = codeblock_converter(code).content
        with misc.StopWatch() as s:
            records = await ctx.bot.connection.fetch(query)

        if not records:
            return await ctx.send(f"Executed in *`{s.time*1000:,.2f}`ms*")

        table = PrettyTable()
        table.field_names = [*records[0].keys()]
        for record in records:
            table.add_row([*record.values()])
        await ctx.send(
            f"Returned {len(records)} rows in *`{s.time*1000:,.2f}ms`*\n```{table.get_string()}```"
        )

    @dev.command()
    @commands.is_owner()
    async def reload(self, ctx, *, extension=None):
        """Reload an extension or all modified extensions"""
        if extension:
            try:
                ctx.bot.reload_extension(extension)
            except Exception:
                await ctx.send(f"```{traceback.format_exc()}```")
            else:
                await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        else:
            message = []
            for extension in ctx.bot.config.extensions:
                file = pathlib.Path(extension.replace(".", "/")+".py")
                if not file.exists():
                    continue
                modified = file.stat().st_mtime
                if modified > ctx.bot.extension_checked_at:
                    try:
                        ctx.bot.reload_extension(extension)
                    except Exception as e:
                        message.append("\N{CROSS MARK}" f" {extension} {e}")
                    else:
                        message.append("\N{WHITE HEAVY CHECK MARK}" f" {extension}")
            if not message:
                message.append("No extensions to reload!")
            ctx.bot.extension_checked_at = time.time()
            await ctx.send("\n".join(message))

    @dev.command(name="eval")
    @commands.is_owner()
    async def _eval(self, ctx, *, code):
        """Evaluate code"""
        code = codeblock_converter(code).content

        code = textwrap.indent(code, "    ")

        code = f"async def func():\n{code}"

        env = {
            "discord": discord,
            "ctx": ctx,
            "guild": ctx.guild,
            "author": ctx.author,
            "bot": ctx.bot,
            "commands": commands,
        }

        exec(code, env)
        func = env["func"]

        stdout = io.StringIO()

        try:
            with redirect_stdout(stdout):
                result = await func()
        except Exception:
            value = stdout.getvalue()
            return await ctx.send(f"```{value}\n{traceback.format_exc()}```")
        value = stdout.getvalue()

        try:
            await ctx.message.add_reaction("\u2705")
        except:
            pass

        output = f"```{value}\n{result}```"
        await ctx.send(output)


def setup(bot):
    bot.add_cog(Admin(bot))
