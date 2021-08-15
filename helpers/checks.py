from discord.ext.commands import check, CheckFailure


def has_started():
    """Checks that the user has started, this also doubles as the blacklist check"""

    async def predicate(ctx):
        disabled = await ctx.bot.connection.fetchval(
            "SELECT disabled FROM users WHERE id = $1", ctx.author.id
        )

        if disabled:
            raise CheckFailure("Your account has been disabled.")
        elif disabled is not None:
            return True

        raise CheckFailure("You have not started yet! Please start first!")

    return check(predicate)
