import discord
import typing

import re
from typing import List, Literal
from collections import defaultdict

from discord.ext import commands
from discord.ext.commands import converter
from helpers import constants, converters, models, checks, flags, methods


class PokemonFilters(flags.PosixFlags):
    name: str = None
    level: int = None
    legendary: bool = False
    mythical: bool = False
    ultrabeast: bool = False
    fav: bool = False


class DexFlags(flags.PosixFlags):
    legendary: bool = False
    ub: bool = commands.flag(aliases=("ultrabeast", "ultra_beast"), default=False)
    mythical: bool = False
    caught: bool = False
    uncaught: bool = False
    order: Literal["a", "d"] = None


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
                name=f"Generation {generation}", value=", ".join(pokemon), inline=False
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
            title=f"Level {pokemon.level} {pokemon.pretty_name}",
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

        embed.compact_image(
            await self.bot.db.get_guild(ctx.guild),
            url=self.bot.data.image(pokemon.species_id, pokemon.shiny),
        )

        embed.set_footer(text=f"Displaying ID: {pokemon.idx}. Global ID: {pokemon.id}")

        await ctx.send(embed=embed)

    @commands.command(aliases=("p",))
    @checks.has_started()
    async def pokemon(
        self, ctx, page: typing.Optional[int] = 1, *, flags: PokemonFilters = None
    ):
        """View your pokemon"""
        constraints, args = self.bot.db.format_query_from_flags(flags, start=4)

        lower = (page - 1) * 15 + 1
        upper = (page) * 15
        query = f"SELECT * FROM (SELECT *, rank() over(order by ({(await self.bot.db.get_user(ctx.author)).order_by})) as rank FROM pokemon WHERE user_id = $1 AND market_price is NULL {constraints}) as _ WHERE user_id = $1 AND market_price is NULL AND rank >= $2 AND rank <= $3 {constraints} ORDER BY rank ASC"
        pokemons = [
            models.Pokemon(pokemon, self.bot.data)
            for pokemon in await self.bot.connection.fetch(
                query,
                ctx.author.id,
                lower,
                upper,
                *args,
            )
        ]
        constraints, _ = self.bot.db.format_query_from_flags(flags, start=2)
        size = await self.bot.connection.fetchval(
            f"SELECT COUNT(id) FROM pokemon WHERE user_id = $1 AND market_price = NULL{constraints}",
            ctx.author.id,
            *args,
        )
        if not pokemons:
            return await ctx.send("No pokémon found.")
        num = max([pokemon.idx for pokemon in pokemons])
        length = len(str(num))
        embed = constants.Embed(title="Your pokemon:", description="")
        embed.set_footer(
            text=f"Displaying {lower}-{min([upper, len(pokemons)])} of {size} pokémon"
        )
        for pokemon in pokemons:
            st = f"`{pokemon.idx:>{length}}` {pokemon.pretty_name} | Level: {pokemon.level} | IV: {pokemon.iv_percent*100:,.2f}%\n"
            embed.description += st

        await ctx.send(embed=embed)

    @commands.command()
    @checks.has_started()
    async def select(self, ctx, pokemon: converters.PokemonConverter):
        """Select a new pokemon to levelup"""
        await self.bot.connection.execute(
            "UPDATE users SET selected = $1 WHERE id = $2", pokemon.idx, ctx.author.id
        )
        await ctx.send(f"Selected {pokemon.pretty_name}, id: {pokemon.idx}")

    @commands.command(aliases=("nick", "rename"))
    @checks.has_started()
    async def nickname(self, ctx, *, nick=None):
        """Change the nickname of your pokemon"""
        if not 0 < len(nick) < 30:
            return await ctx.send("Invalid size of nickname")

        await self.bot.db.update_selected_pokemon(ctx.author, dict(nick=nick))
        if nick:
            await ctx.send(f"You have changed your pokemon's nickname to {nick}")
        else:
            await ctx.send(f"You have reset your pokemon's nickname")

    @commands.command(aliases=("addfav", "addfavorite", "fav"))
    @checks.has_started()
    async def favorite(self, ctx, pokemon: converters.PokemonConverter = None):
        """Favorite your selected pokemon"""
        if not pokemon:
            await self.bot.db.update_selected_pokemon(ctx.author, dict(favorite=True))
            return await ctx.send("You have favorited your selected pokemon")

        await self.bot.db.update_pokemon_by_idx(
            ctx.author, pokemon.idx, dict(favorite=True)
        )
        await ctx.send(f"You have favorited the pokemon with the id of {pokemon.idx}")

    @commands.command(aliases=("removefav", "removefavorite", "unfav"))
    @checks.has_started()
    async def unfavorite(self, ctx):
        """Favorite your selected pokemon"""
        await self.bot.db.update_selected_pokemon(ctx.author, dict(favorite=False))
        await ctx.send("You have unfavorited your selected pokemon")

    async def pokemon_dex(self, ctx, pokemon):
        pokemon, shiny = pokemon
        embed = constants.Embed(
            title=f"#{pokemon['species_id']} - {'✨' if shiny else ''}{pokemon['english'].title()}",
            description=pokemon["sun"],
        )
        embed.add_field(
            name="Alternate Names",
            value=(
                f"\U0001f1fa\U0001f1f8 {pokemon['english']}\n"
                f"\U0001f1ef\U0001f1f5 {pokemon['japanese']}\n"
                f"\U0001f1ef\U0001f1f5 {pokemon['kana']}\n"
            ),
            inline=False,
        )
        embed.add_field(
            name="Base Stats",
            value=(
                f"**HP:** {pokemon['hp']}\n"
                f"**Attack:** {pokemon['attack']}\n"
                f"**Defense:** {pokemon['defense']}\n"
                f"**Sp. Atk:** {pokemon['special_attack']}\n"
                f"**Sp. Defense:** {pokemon['special_defense']}\n"
                f"**Speed:** {pokemon['speed']}\n"
            ),
        )
        embed.add_field(name="Types", value=(", ".join(pokemon["types"])))
        embed.compact_image(
            await self.bot.db.get_guild(ctx.guild),
            url=self.bot.data.image(pokemon["species_id"], shiny=shiny),
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=("dex", "d"), usage="<pokemon/page>")
    async def pokedex(self, ctx, *args):
        """View infomation on a pokemon or view all your dex infomation on pokemon"""
        try:
            pokemon = await converters.DexConverter().convert(ctx, " ".join(args))
        except commands.BadArgument:
            await checks.has_started().predicate(ctx)
            if len(args) and methods.is_int(args[0]):
                page = int(args[0])
                args = args[1:]
            else:
                page = 1

            if args:
                content = re.sub(
                    rf"--([^\s]+)(?=(\s--)|$)",
                    rf"--\1 true",
                    " ".join(args),
                )
                flags = await DexFlags.convert(ctx, content)
            else:
                flags = None

            dex = await ctx.bot.db.get_dex(ctx.author)
            entries = self.bot.data.data
            key = None
            reverse = False
            if flags:
                if flags.caught:
                    entries = {
                        species_id: data
                        for species_id, data in entries.items()
                        if dex.get(species_id)
                    }
                elif flags.uncaught:
                    entries = {
                        species_id: data
                        for species_id, data in entries.items()
                        if not dex.get(species_id)
                    }

                if flags.order:

                    def key(item):
                        if entry := dex.get(item):
                            return 60000 + entry.count
                        return item

                    if flags.order == "d":
                        reverse = True

                if flags.legendary:
                    entries = self.bot.data.legendary
                elif flags.mythical:
                    entries = self.bot.data.mythical
                elif flags.ub:
                    entries = self.bot.data.ultra_beast

            dex = {i: v for i, v in dex.items() if i in entries}
            ids = list(range((page - 1) * 20, page * 20))

            embed = constants.Embed(
                title="Pokédex",
                description=f"You've caught {len(dex)} of {len(entries)} pokémon.",
            )

            for idx, species_id in enumerate(
                sorted(entries.keys(), key=key, reverse=reverse)
            ):
                data = entries[species_id]
                if idx not in ids:
                    continue
                if entry := dex.get(species_id):
                    message = f"{entry.count} caught!" " \N{WHITE HEAVY CHECK MARK}"
                else:
                    message = "Not caught yet! \N{CROSS MARK}"
                embed.add_field(name=f"{data['english']} #{species_id}", value=message)

            await ctx.send(embed=embed)

        else:
            return await self.pokemon_dex(ctx, pokemon)


def setup(bot):
    bot.add_cog(Pokemon(bot))
