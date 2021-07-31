import discord
from discord.ext import commands

class Admin(commands.Cog):
    """Commands for bot administration"""
    @commands.group(case_insensitive=True)
    @commands.is_owner()
    async def dev(self, ctx):
        """The group command for development commands"""
        if ctx.invoked_subcommand is None:
           await ctx.send_help(ctx.command)

    @dev.command()
    async def random_spawn(self, ctx):
        """Spawn a random pokemon"""
        await ctx.bot.get_cog("Spawning").spawn_pokemon(ctx.channel)

    @dev.command()
    async def spawn(self, ctx, *, pokemon):
        await ctx.bot.get_cog("Spawning").spawn_pokemon(ctx.channel, pokemon)

    @dev.command()
    async def give_pokemon(self, ctx, target: discord.Member, *, pokemon):
        """Add pokemon to a user"""
        shiny=False
        if pokemon.startswith("shiny"):
            shiny=True
            pokemon = pokemon.replace("shiny ", "")
        pokemon = ctx.bot.data.get_species_by_name(pokemon)
        if not pokemon:
            return await ctx.send("invalid pokemon")

        await ctx.bot.db.insert_pokemon(
            target, pokemon["species_id"], shiny=shiny
        )
        await ctx.message.add_reaction("\U00002705")


def setup(bot):
    bot.add_cog(Admin(bot))
    
