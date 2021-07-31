from discord.ext import commands
from helpers.models import Pokemon


class PokemonConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if not argument:
            argument = await ctx.bot.connection.fetchval(
                "SELECT selected FROM users WHERE id = $1", ctx.author.id
            )
        elif argument.lower() in ("l", "latest"):
            argument = 0
        else:
            argument = int(argument)
        async with ctx.bot.connection.acquire() as conn:
            async with conn.transaction():
                count = await ctx.bot.db.get_next_idx(ctx.author, connection=conn)
                count -= 1
                if argument < 1:
                    argument = count - argument
                pokemon = await ctx.bot.db.get_pokemon_by_idx(
                    ctx.author, argument, connection=conn
                )

        if not pokemon:
            raise commands.BadArgument("No pokemon found with that id")
        return Pokemon(pokemon, ctx.bot.data)


class DexConverter(commands.Converter):
    async def convert(self, ctx, argument):
        argument = argument.lower()
        shiny = False
        if argument.startswith("shiny"):
            shiny = True
            argument = argument.replace("shiny ", "")
            print(argument)
        if argument.isdigit():
            if pokemon := ctx.bot.data.get_species_by_id(int(argument)):
                return pokemon, shiny

        elif pokemon := ctx.bot.data.get_species_by_name(argument):
            return pokemon, shiny

        return None
