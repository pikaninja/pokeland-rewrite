import discord
from discord.ext import commands
from helpers import constants, converters

class Pokemon(commands.Cog):
    """General pokemon commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def start(self, ctx):
        """Begin your journey into the world of pokemon!"""
        embed = constants.Embed(title=f"Welcome {ctx.author.display_name} to the word of pokémon!", description=f"To choose your starter, use `{ctx.prefix}pick <pokemon>`")
        for generation, pokemon in constants.STARTERS.items():
            embed.add_field(name=f"Generation {generation}", value=",".join(pokemon), inline=False)
        
        await ctx.send(embed=embed)

    @commands.command()
    async def pick(self, ctx, *, pokemon: str):
        pokemon = self.bot.data.get_species_by_name(pokemon)
        if not pokemon:
            return await ctx.send("Thats not a valid pokemon!")
        starters = [name.lower() for pokemons in constants.STARTERS.values() for name in pokemons]
        if pokemon["name"] not in starters:
            return await ctx.send("Thats not a starter pokemon!")
        async with self.bot.connection.acquire() as conn:
            async with conn.transaction():
                if not await self.bot.db.register(ctx.author, connection = conn):
                    return await ctx.send("You have already started!")

                await self.bot.db.insert_pokemon(ctx.author, pokemon["id"], connection = conn)

        await ctx.send(f"You have begun your journey! Use `{ctx.prefix}info` to view your new friend and `{ctx.prefix}pokemon` to view all your pokemon!")

    @commands.command(aliases=("i", "infomation"))
    async def info(self, ctx, pokemon: converters.PokemonConverter=None):
        if not pokemon:
            pokemon = await converters.PokemonConverter().convert(ctx, "")
        data = self.bot.data.get_species_by_id(pokemon.species_id)
        embed = constants.Embed(
            title=f"Level {pokemon.level} {data['name']}",
            description=f"**XP**: {pokemon.xp}\n**Nature:** {pokemon.nature}"
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
            )
        )

        if pokemon.item:
            embed.add_field(name="Held Item", value=pokemon.item)

        embed.set_image(url=data['shiny'] if pokemon.shiny else data['normal'])

        await ctx.send(embed=embed)




def setup(bot):
    bot.add_cog(Pokemon(bot))

 



