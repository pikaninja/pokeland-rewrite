
from discord.ext.commands import check, CheckFailure


def has_started():
    async def predicate(ctx):
        if await ctx.bot.connection.fetchval(
            "SELECT 1 FROM users WHERE id = $1", ctx.author.id
        ):
            return True

        raise CheckFailure("You have not started yet! Please start first!")

    return check(predicate)
