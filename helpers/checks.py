from discord.ext.commands import check


def has_started():
    async def predicate(ctx):
        return await ctx.bot.connection.fetchval(
            "SELECT 1 FROM users WHERE id = $1", ctx.author.id
        )

    return check(predicate)
