import datetime
from typing import NamedTuple

from discord import file

import discord
from helpers import constants
from discord.ext import commands


class ExpiredCache(NamedTuple):
    count: int
    expires: datetime.datetime


class Tutorial:
    """A tutorial for a specifix user"""

    def __init__(self, user, channel, prefix="p!"):
        self.channel = channel
        self.user = user
        self.prefix = prefix

    @property
    def catching(self):
        embed = constants.Embed(
            title="Obtaining pokemon",
            description=(
                "As you talk, pokemon will spawn in your server. "
                f"You can catch them with {self.prefix}catch <pokemon>"
            ),
        )
        embed.set_image(url="attachment://catching.png")
        return (embed, discord.File("assets/catching.png", filename="catching.png"))


class Information(commands.Cog):
    """Commands to view bot information and help"""

    def __init__(self, bot):
        self.bot = bot
        self.user_count = None
        self.pokemon_count = None
        self.bot.help_command.cog = self

    async def count_users(self):
        if self.user_count and self.user_count.expires >= datetime.datetime.utcnow():
            return self.user_count.count
        else:
            self.user_count = ExpiredCache(
                await self.bot.connection.fetchval("SELECT COUNT(id) FROM users"),
                datetime.datetime.utcnow(),
            )
            return self.user_count.count

    async def count_pokemon(self):
        if (
            self.pokemon_count
            and self.pokemon_count.expires >= datetime.datetime.utcnow()
        ):
            return self.pokemon_count.count
        else:
            self.pokemon_count = ExpiredCache(
                await self.bot.connection.fetchval("SELECT COUNT(id) FROM pokemon"),
                datetime.datetime.utcnow(),
            )
            return self.pokemon_count.count

    @commands.command(aliases=("bot",))
    async def botinfo(self, ctx):
        """View some basic infomation of the bot"""
        embed = constants.Embed(
            title="Pokeland",
            description="Pokeland is a bot to bring the pokemon experience to your servers!",
        )
        embed.set_thumbnail(url=ctx.me.avatar.url)
        embed.add_field(name="Trainers", value=f"{await self.count_users():,}")
        embed.add_field(
            name="Pokemon", value=f"{await self.count_pokemon():,}", inline=False
        )
        embed.add_field(name="Guilds", value=f"{len(ctx.bot.guilds):,}", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def tutorial(self, ctx):
        """View a tutorial for the bot"""
        # TODO: MAKE NOT STUPID
        tutorial = Tutorial(ctx.author, ctx.channel, ctx.prefix)
        embed, file = tutorial.catching
        await ctx.send(embed=embed, file=file)


def setup(bot):
    bot.add_cog(Information(bot))
