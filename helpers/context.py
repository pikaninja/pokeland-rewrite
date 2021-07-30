from discord.ext import commands


class PokeContext(commands.Context):
    pass


def setup(bot):
    bot.context = PokeContext


def teardown(bot):
    bot.context = commands.Context
