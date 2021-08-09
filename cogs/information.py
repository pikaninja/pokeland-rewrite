import datetime
from typing import NamedTuple

from discord import file

import discord
from helpers import constants, misc
from discord.ext import commands


class ExpiredCache(NamedTuple):
    count: int
    expires: datetime.datetime


class TutorialSelect(discord.ui.Select):
    def __init__(self, tutorial):
        self.tutorial = tutorial
        super().__init__(
            placeholder="Select a cateogyr",
            options=[
                discord.components.SelectOption(
                    label=t, value=t, description=getattr(Tutorial, t).__doc__
                )
                for t in self.tutorial.CATEGORIES
            ],
        )

    async def callback(self, interaction):
        category = self.values[0]
        await self.tutorial.message.delete()
        embed, file = getattr(self.tutorial, category)
        await interaction.response.send_message(embed=embed, file=file, view=self.view)


class Tutorial:
    """A tutorial for a specifix user"""

    CATEGORIES = [
        "catching",
    ]

    def __init__(self, bot, user, channel, prefix="p!"):
        self.bot = bot
        self.channel = channel
        self.user = user
        self.prefix = prefix

    async def start(self):
        print(self.catching.__doc__)
        embed = constants.Embed(
            title="Pokeland tutorial",
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        view = misc.RestrictedView(owner=self.user)
        view.add_item(TutorialSelect(self))
        self.message = await self.channel.send(embed=embed, view=view)

    @property
    def catching(self):
        """Obtaining pokemon"""
        embed = constants.Embed(
            title="Obtaining pokemon",
            description=(
                "As you talk, pokemon will spawn in your server. "
                f"You can catch them with {self.prefix}catch <pokemon>"
            ),
        )
        embed.set_footer(
            text="You can also trade pokemon with other users! See trade and market"
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
        tutorial = Tutorial(ctx.bot, ctx.author, ctx.channel, ctx.prefix)
        await tutorial.start()


def setup(bot):
    bot.add_cog(Information(bot))
