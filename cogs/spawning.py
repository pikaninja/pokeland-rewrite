import random
import discord
from collections import defaultdict
from discord.ext import commands
from helpers import constants


class Spawning(commands.Cog):
    """The category for spawning pokemon"""

    def __init__(self, bot):
        self.bot = bot

        def default_spawn():
            return dict(pokemon=None, count=0, goal=random.randint(25, 50))

        self.spawns = defaultdict(default_spawn)

    def random_pokemon(self):
        pokemon = list(self.bot.data.data.values())
        pokemon = random.choices(
            pokemon, weights=[x.get("abundance", 0) for x in pokemon], k=1
        )[0]
        return pokemon

    async def spawn_pokemon(self, channel):
        pokemon = self.random_pokemon()
        self.spawns[channel.id]["pokemon"] = pokemon
        self.spawns[channel.id]["count"] = 0
        self.spawns[channel.id]["goal"] = random.randint(25, 50)
        embed = constants.Embed(
            title="A wild pokemon as appeared!",
            description=f"Guess the pokémon's name and type `{'p!'}catch <pokemon>` to catch it!",
        )
        embed.set_image(url=pokemon["normal"])

        await channel.send(embed=embed)

    @commands.command(aliases=("capture",))
    @commands.max_concurrency(1, commands.BucketType.channel)
    async def catch(self, ctx, *, pokemon):
        pokemon = self.bot.data.get_species_by_name(pokemon)
        if not pokemon:
            return await ctx.send("That's not a pokémon!")

        if not self.spawns[ctx.channel.id]["pokemon"]:
            return

        if (
            pokemon["species_id"]
            != self.spawns[ctx.channel.id]["pokemon"]["species_id"]
        ):
            return await ctx.send("That's not the correct pokémon!")

        self.spawns[ctx.channel.id]["pokemon"] = None

        percentage = 1 / 4096  # in future make changable
        shiny = random.random() <= percentage

        pokemon = await self.bot.db.insert_pokemon(
            ctx.author, pokemon["species_id"], shiny=shiny
        )

        await ctx.send(
            f"Congratulations {ctx.author.mention}! You caught a level {pokemon.level} {'✨' if shiny else ''}{pokemon.name}!"
        )

    @commands.Cog.listener("on_message")
    async def spawning(self, message):
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        self.spawns[message.channel.id]["count"] += 1
        if (
            self.spawns[message.channel.id]["count"]
            >= self.spawns[message.channel.id]["goal"]
        ):
            await self.spawn_pokemon(message.channel)


def setup(bot):
    bot.add_cog(Spawning(bot))
