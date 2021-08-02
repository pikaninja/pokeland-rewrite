import io
import discord
import traceback

from typing import Literal, Union

from discord.ext import commands
from helpers import constants, misc, checks


class Meta(commands.Cog):
    """Commands for bot configuration"""

    def __init__(self, bot):
        self.bot = bot

    async def bot_check(self, ctx):
        channel = await self.bot.db.get_channel(ctx.channel)
        if not channel:
            return True
        if channel.disabled and ctx.command != self.enable:
            raise commands.CheckFailure(
                "Commands in this channel are currently disabled!"
            )
        return True

    async def get_prefix(self, guild):
        guild = await self.bot.db.get_guild(guild.id)
        if not guild:
            return self.bot.config.prefix
        return guild.prefix or self.bot.config.prefix

    @commands.command(usage="<commands/spawns>")
    async def disable(
        self, ctx, feature: Literal["command", "spawns", "commands", "spawn"]
    ):
        """Disable specific features in the channel for the bot, note that if you disable commands, spawns will be disabled too"""
        if feature in ("command", "commands"):
            await self.bot.connection.execute(
                "INSERT INTO channels(id, guild_id, disabled) VALUES($1, $2, true) ON CONFLICT(id) DO UPDATE SET disabled=true",
                ctx.channel.id,
                ctx.guild.id,
            )
        else:
            await self.bot.connection.execute(
                "INSERT INTO channels(id, guild_id, spawns_disabled) VALUES($1, $2, true) ON CONFLICT(id) DO UPDATE SET spawns_disabled=true",
                ctx.channel.id,
                ctx.guild.id,
            )

        await ctx.send(f"I have disabled `{feature}`")

    @commands.command(usage="<commands/spawns>")
    async def enable(
        self, ctx, feature: Literal["command", "spawns", "commands", "spawn"]
    ):
        """Enable disabled features in the channel"""
        if feature in ("command", "commands"):
            await self.bot.connection.execute(
                "UPDATE channels SET disabled = false WHERE id = $1", ctx.channel.id
            )
        else:
            await self.bot.connection.execute(
                "UPDATE channels SET spawns_disabled = false WHERE id = $1",
                ctx.channel.id,
            )

        await ctx.send(f"I have enabled `{feature}`")

    @commands.command(usage="<toggle/true/false>")
    async def compact(self, ctx, option: Literal["toggle", "true", "false"]):
        """Controls whether or not to send messages on levelup"""
        if option == "toggle":
            toggle = await ctx.bot.connection.fetchval(
                "INSERT INTO guilds(id, compact) VALUES($1, true) ON CONFLICT(id) DO UPDATE SET compact = NOT (SELECT compact FROM guilds WHERE id = $1) RETURNING compact",
                ctx.guild.id,
            )
        else:
            option = True if option == "true" else False
            toggle = await ctx.bot.connection.fetchval(
                "INSERT INTO guilds(id, compact) VALUES($1, $2) ON CONFLICT(id) DO UPDATE SET compact = $2 RETURNING compact",
                ctx.guild.id,
                option,
            )

        if toggle:
            await ctx.send("Alright, I will compact images")
        else:
            await ctx.send("Alright, I will no longer compact images")

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def redirect(self, ctx, channels: commands.Greedy[discord.TextChannel]):
        """Config the redirect settings for the server, when set, all spawns will be redirected to these channels"""
        if not channels:
            guild = await ctx.bot.db.get_guild(ctx.guild)
            if not guild or not guild.redirects:
                return await ctx.send("There's no redirects active currently!")
            return await ctx.send(
                f"The current redirected channels are {', '.join(f'<#{id}>' for id in guild.redirects)}"
            )

        await ctx.bot.connection.execute(
            "INSERT INTO guilds(id, redirects) VALUES ($1, $2) ON CONFLICT(id) DO UPDATE SET redirects = $2",
            ctx.guild.id,
            [channel.id for channel in channels],
        )
        await ctx.send(
            f"Set the redirects to {', '.join(channel.mention for channel in channels)} All pokemon will be redirected to these channels!"
        )

    @commands.command(aliases=("silence", "hide"), usage="<toggle/true/false>")
    @checks.has_started()
    async def hide_levelup(self, ctx, option: Literal["toggle", "true", "false"]):
        """Toggles whether or not to send messages on levelup"""
        if option == "toggle":
            toggle = await ctx.bot.connection.fetchval(
                "UPDATE users SET hide_levelup = NOT hide_levelup WHERE id = $1 RETURNING hide_levelup",
                ctx.author.id,
            )
        else:
            option = True if option == "true" else False
            toggle = await ctx.bot.connection.fetchval(
                "UPDATE users SET hide_levelup = $2 WHERE id = $1 RETURNING hide_levelup",
                ctx.author.id,
                option,
            )

        if toggle:
            await ctx.send("Alright, I will no longer send levelup messages.")
        else:
            await ctx.send("Alright, I will send levelup messages again")

    @commands.group(invoke_without_command=True, case_insensitive=True)
    async def prefix(self, ctx):
        """The group command for prefix management, use with no subcommand to view current prefix"""
        await ctx.send(
            f"The current prefix is `{await self.get_prefix(ctx.channel.guild)}` You can also mention me!"
        )

    @prefix.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def set(self, ctx, prefix):
        """Set the prefix for the guild to somethign else"""
        await self.bot.connection.execute(
            "INSERT INTO guilds(id, prefix) VALUES($1, $2) ON CONFLICT(id) DO UPDATE SET prefix=$2",
            ctx.guild.id,
            prefix,
        )
        await ctx.send(f"Set the server prefix to `{prefix}`")

    @prefix.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def reset(self, ctx, prefix):
        """Reset the prefix to the default prefix"""
        await self.bot.connection.execute(
            "UPDATE guilds SET prefix=$1 WHERE id = $2", None, ctx.guild.id
        )
        await ctx.send(f"Reset the guild prefix to `{self.bot.config.prefix}`")

    @commands.command()
    async def ping(self, ctx):
        """Pong!"""
        message = await ctx.send("Pong!")
        delay = int(
            1000 * (message.created_at - ctx.message.created_at).total_seconds()
        )

        if await self.bot.is_owner(ctx.author):
            with misc.StopWatch() as s:
                await self.bot.connection.execute("SELECT 1;")

            await message.edit(
                content=f"Pong! **{delay} ms**. **{s.time*1000:,.2f} ms db ping**, **{int(self.bot.latency*1000)} ms websocket**"
            )

        else:
            await message.edit(content=f"Pong! **{delay} ms**")


def setup(bot):
    bot.add_cog(Meta(bot))
