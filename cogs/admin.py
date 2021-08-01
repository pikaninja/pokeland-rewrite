import io
import discord
import textwrap
import traceback

from contextlib import redirect_stdout

from helpers import misc
from discord.ext import commands
from prettytable import PrettyTable
from jishaku.codeblocks import codeblock_converter

class Admin(commands.Cog):
    """Commands for bot administration"""

    @commands.group(case_insensitive=True)
    @commands.is_owner()
    async def dev(self, ctx):
        """The group command for development commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @dev.command()
    async def random_spawn(self, ctx):
        """Spawn a random pokemon"""
        await ctx.bot.get_cog("Spawning").spawn_pokemon(ctx.channel)

    @dev.command()
    async def spawn(self, ctx, *, pokemon):
        await ctx.bot.get_cog("Spawning").spawn_pokemon(ctx.channel, pokemon)

    @dev.command()
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

    @dev.command(name="eval")
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
