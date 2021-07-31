import discord
import typing
from typing import List
from discord.ext import commands
from collections import defaultdict
from helpers import constants, converters, models, checks, flags


class PokemonFilters(flags.PosixFlags):
    name: List[str] = None
    level: List[int] = None
    legendary: bool = False
    mythical: bool = False
    ultra_beast: bool = False
    _or: bool = commands.flag(name="or", default=False)


class Pokemon(commands.Cog):
    """General pokemon commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def start(self, ctx):
        """Begin your journey into the world of pokemon!"""
        embed = constants.Embed(
            title=f"Welcome {ctx.author.display_name} to the word of pokémon!",
            description=f"To choose your starter, use `{ctx.prefix}pick <pokemon>`",
        )
        for generation, pokemon in constants.STARTERS.items():
            embed.add_field(
                name=f"Generation {generation}", value=",".join(pokemon), inline=False
            )

        await ctx.send(embed=embed)

    @commands.command()
    async def pick(self, ctx, *, pokemon: str):
        """Select your starter"""
        pokemon = self.bot.data.get_species_by_name(pokemon)
        if not pokemon:
            return await ctx.send("Thats not a valid pokemon!")
        starters = [
            name.lower()
            for pokemons in constants.STARTERS.values()
            for name in pokemons
        ]
        if pokemon["name"] not in starters:
            return await ctx.send("Thats not a starter pokemon!")
        async with self.bot.connection.acquire() as conn:
            async with conn.transaction():
                if not await self.bot.db.register(ctx.author, connection=conn):
                    return await ctx.send("You have already started!")

                await self.bot.db.insert_pokemon(
                    ctx.author, pokemon["species_id"], connection=conn
                )

        await ctx.send(
            f"You have begun your journey! Use `{ctx.prefix}info` to view your new friend and `{ctx.prefix}pokemon` to view all your pokemon!"
        )

    @commands.command(aliases=("i", "infomation"))
    @checks.has_started()
    async def info(self, ctx, pokemon: converters.PokemonConverter = None):
        """View infomation on your pokemon"""
        if not pokemon:
            pokemon = await converters.PokemonConverter().convert(ctx, "")
        data = self.bot.data.get_species_by_id(pokemon.species_id)
        embed = constants.Embed(
            title=f"Level {pokemon.level} {pokemon.name}",
            description=f"**XP**: {pokemon.xp}/{pokemon.xp_needed}\n**Nature:** {pokemon.nature}",
        )
        embed.add_field(
            name="Stats",
            value=(
                f"**HP:** {pokemon.stat('hp')} - IV: {pokemon.hp_iv}/31\n"
                f"**Attack:** {pokemon.stat('atk')} - IV: {pokemon.atk_iv}/31\n"
                f"**Defense:** {pokemon.stat('def')} - IV: {pokemon.def_iv}/31\n"
                f"**Sp. Atk:** {pokemon.stat('spatk')} - IV: {pokemon.spatk_iv}/31\n"
                f"**Sp. Def:** {pokemon.stat('spdef')} - IV: {pokemon.spdef_iv}/31\n"
                f"**Speed:** {pokemon.stat('spd')} - IV: {pokemon.spd_iv}/31\n"
                f"**Total:**  {pokemon.iv_percent*100:,.2f}%"
            ),
        )

        if pokemon.item:
            embed.add_field(name="Held Item", value=pokemon.item)

        embed.set_image(url=data["shiny"] if pokemon.shiny else data["normal"])

        await ctx.send(embed=embed)

    @commands.command(aliases=("p",))
    @checks.has_started()
    async def pokemon(
        self, ctx, page: typing.Optional[int] = 1, *, flags: PokemonFilters = None
    ):
        """View your pokemon"""
        filters = defaultdict(list)
        if flags and flags.name:
            filters["species_id"].extend([self.bot.data.get_species_by_name(name)["species_id"] for name in flags.name])
        if flags and flags.level:
            filters["level"].extend([level for level in flags.level])
        if flags and flags.legendary:
            filters["in_species_id"].append(list(self.bot.data.legendary.keys()))
        if flags and flags.mythical:
            filters["in_species_id"].append(list(self.bot.data.mythical.keys()))
        if flags and flags.ultra_beast:
            filters["in_species_id"].append(list(self.bot.data.ultra_beast.keys()))

        if filters:
            query, args = self.bot.db.format_query_list(filters, _or = flags._or, start=5)
            query = f"AND ({query})"
        else:
            query = ""
            args = []
        lower = (page - 1) * 20 + 1
        upper = (page) * 20
        query = (
            f"SELECT * FROM (SELECT *, rank() over(order by ($1)) as rank FROM pokemon) as _ WHERE user_id = $2 AND rank >= $3 AND rank <= $4 {query} ORDER BY rank ASC"
        )
        pokemons = [
            models.Pokemon(pokemon, self.bot.data)
            for pokemon in await self.bot.connection.fetch(
                query,
                (await self.bot.db.get_user(ctx.author)).order_by,
                ctx.author.id,
                lower,
                upper,
                *args
            )
        ]
        if not pokemons:
            return await ctx.send("No pokémon found.")
        num = max([pokemon.idx for pokemon in pokemons])
        length = len(str(num))
        embed = constants.Embed(title="Your pokemon:", description="")
        embed.set_footer(
            text=f"Displaying {lower}-{min([upper, len(pokemons)])} of {len(pokemons)} pokémon"
        )
        for pokemon in pokemons:
            st = f"`{pokemon.idx:>{length}}` {pokemon.name} | Level: {pokemon.level} | IV: {pokemon.iv_percent*100:,.2f}%\n"
            embed.description += st

        await ctx.send(embed=embed)

    @commands.command(aliases = ("dex",))
    async def pokedex(self, ctx, *, pokemon: converters.DexConverter):
        """View infomation on a pokemon"""
        pokemon, shiny = pokemon
        embed = constants.Embed(title=f"#{pokemon['species_id']} - {'✨' if shiny else ''}{pokemon['english'].title()}", description = pokemon['sun'])
        embed.add_field(name="Alternate Names", value=(
            f"\U0001f1fa\U0001f1f8 {pokemon['english']}\n"
            f"\U0001f1ef\U0001f1f5 {pokemon['japanese']}\n"
            f"\U0001f1ef\U0001f1f5 {pokemon['kana']}\n"
        ), inline=False)
        embed.add_field(name="Base Stats", value=(
            f"**HP:** {pokemon['hp']}\n"
            f"**Attack:** {pokemon['attack']}\n"
            f"**Defense:** {pokemon['defense']}\n"
            f"**Sp. Atk:** {pokemon['special_attack']}\n"
            f"**Sp. Defense:** {pokemon['special_defense']}\n"
            f"**Speed:** {pokemon['speed']}\n"
        ))
        embed.add_field(name="Types", value=(
            ", ".join(pokemon['types'])
        ))
        embed.set_image(url=pokemon['normal'] if not shiny else pokemon['shiny'])
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Pokemon(bot))
