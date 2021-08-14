import io
import sys
import copy
import time
import psutil
import discord
import pathlib
import textwrap
import datetime
import traceback
import importlib
import dataclasses

from typing import Union
from contextlib import redirect_stdout

from helpers import misc, constants
from discord.ext import commands
from prettytable import PrettyTable
from jishaku.codeblocks import codeblock_converter

@dataclasses.dataclass
class BenchmarkTime:
    total: float
    count: int
    low: float
    high: float
    @property
    def average(self):
        return self.total/self.count

    def update(self, time):
        self.total += time
        self.count += 1
        if time < self.low:
            self.low = time
        if time > self.high:
            self.high = time

    def __str__(self):
        return f"Average: `{self.average*1000:,.2f}ms`\nHigh: `{self.high*1000:,.2f}ms`\nLow: `{self.low*1000:,.2f}ms`"

class Admin(commands.Cog):
    """Commands for bot administration"""
    def __init__(self, bot):
        if not hasattr(bot, "extension_checked_at"):
            bot.extension_checked_at = time.time()
        self.process = psutil.Process()

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
    async def benchmark(self, ctx, times=100):
        """Benchmark postgresql"""
        insert = BenchmarkTime(0, 0, 999, -1)
        delete = BenchmarkTime(0, 0, 999, -1)
        update = BenchmarkTime(0, 0, 999, -1)
        query = BenchmarkTime(0, 0, 999, -1)
        async with ctx.bot.connection.acquire() as conn:
            async with conn.transaction(): 
                for i in range(times):
                    with misc.StopWatch() as s:
                        pokemon = await ctx.bot.db.insert_pokemon(ctx.author, 1, connection=conn)
                    insert.update(s.time) 

                    with misc.StopWatch() as s:
                        await ctx.bot.db.update_pokemon_by_idx(ctx.author, pokemon.idx, dict(species_id=2), connection=conn)
                    update.update(s.time)

                    with misc.StopWatch() as s:
                        await ctx.bot.db.get_pokemon_by_idx(ctx.author, pokemon.idx, connection=conn)
                    query.update(s.time)

                    with misc.StopWatch() as s:
                        await conn.execute("DELETE FROM pokemon WHERE id = $1", pokemon.id)
                    delete.update(s.time) 
        
        await ctx.send(
            embed=constants.Embed(
                title="Benchmarks for PostgreSQL",
                description=f"Of {times} times"
            ).add_field(
                name="Insert", 
                value=str(insert)
            ).add_field(
                name="Delete",
                value=str(delete)
            ).add_field(
                name="Update",
                value=str(update)
            ).add_field(
                name="Query",
                value=str(query)
            )
        )
            


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
            if extension.startswith("module."):
                extension = extension.replace("module.", "")
                try:
                    module = __import__(extension)
                    importlib.reload(module)
                except Exception:
                    return await ctx.send(f"```{traceback.format_exc()}```")
                else:
                    return await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
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

    @dev.command(aliases=("sys", "sysinfo", "systeminfo"))
    @commands.is_owner()
    async def system(self, ctx):
        """View system information"""
        embed = constants.Embed(title="System Infomation")
        embed.add_field(name="Library", value=f"v{discord.__version__}")
        embed.add_field(name="Python", value=f"v{sys.version}")
        embed.add_field(name="OS", value=sys.platform)
        embed.add_field(name="API", value=discord.http.Route.BASE)
        embed.add_field(name="Latency", value=f"`{ctx.bot.latency*1000:,.2f}`ms")

        memory_usage = self.process.memory_full_info().uss / 1024 ** 2
        cpu_usage = self.process.cpu_percent()
        embed.add_field(
            name="Process",
            value=f"{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU\n{self.process.num_threads()} threads",
        )

        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        memory = psutil.virtual_memory()
        embed.add_field(
            name="System",
            value=f"Memory: `{memory.used/1000000:,.2f}` MiB used out of `{memory.total/1000000:,.2f}` MiB(`{memory.percent}` percent)\n Booted at {boot_time}",
        )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Admin(bot))
