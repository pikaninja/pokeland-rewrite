import time
import random
import discord
from collections import defaultdict
from discord.ext import commands
from helpers import constants, models


class Spawning(commands.Cog):
    """The category for spawning pokemon"""

    def __init__(self, bot):
        self.bot = bot

        def default_spawn():
            return dict(pokemon=None, count=0, goal=random.randint(25, 50), timestamp = None)

        self.spawns = defaultdict(default_spawn)
        self.cooldown = {}

    def random_pokemon(self):
        pokemon = list(self.bot.data.data.values())
        pokemon = random.choices(
            pokemon, weights=[x.get("abundance", 0) for x in pokemon], k=1
        )[0]
        return pokemon

    async def spawn_pokemon(self, channel, pokemon=None):
        pokemon = self.bot.data.get_species_by_name(pokemon) if pokemon else self.random_pokemon()
        self.spawns[channel.id]["pokemon"] = pokemon
        self.spawns[channel.id]["count"] = 0
        self.spawns[channel.id]["goal"] = random.randint(25, 50)
        self.spawns[channel.id]["timestamp"] = time.perf_counter()
        embed = constants.Embed(
            title="A wild pokemon as appeared!",
            description=f"Guess the pokémon's name and type `{await self.bot.get_cog('Meta').get_prefix(channel.guild)}catch <pokemon>` to catch it!",
        )
        embed.set_image(url=pokemon["normal"])

        await channel.send(embed=embed)

    @commands.command(aliases=("capture",))
    @commands.max_concurrency(1, commands.BucketType.channel)
    async def catch(self, ctx, *, pokemon):
        """Catch a pokemon!"""
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

        if time.perf_counter()-self.spawns[ctx.channel.id]["timestamp"]:
            self.bot.logger.info(
                "User caught pokemon in under a second", 
                extra={
                    "id": ctx.author.id,
                    "tag": str(ctx.author),
                    "guild_id": ctx.guild.id,
                    "guild": ctx.guild,
                    "content": ctx.message.content
                }
            )
        self.spawns[ctx.channel.id]["pokemon"] = None

        percentage = 1 / 4096  # in future make changable
        shiny = random.random() <= percentage

        pokemon = await self.bot.db.insert_pokemon(
            ctx.author, pokemon["species_id"], shiny=shiny
        )

        await ctx.send(
            f"Congratulations {ctx.author.mention}! You caught a level {pokemon.level} {'✨' if shiny else ''}{pokemon.name}!"
        )

    async def calculate_xp(self, message):
        async with self.bot.connection.acquire() as conn:
            async with conn.transaction():
                user = await self.bot.db.get_user(message.author, connection=conn)
                if not user:
                    return
                pokemon = models.Pokemon(await self.bot.db.get_pokemon_by_idx(message.author, user.selected, connection=conn), self.bot.data)
                if pokemon.item == "XP Blocker":
                    return
                if pokemon.level ==  100:
                    return

                xp = random.randint(10, 40)*10

                pokemon.xp += xp
               
                if pokemon.xp >= pokemon.xp_needed:
                    embed = constants.Embed(title = f"Congratulations {message.author.display_name}!")
                    while pokemon.xp >= pokemon.xp_needed:
                        pokemon.xp -= pokemon.xp_needed
                        pokemon.level += 1
                    if not user.hide_levelup:
                        embed.description = f"Your {pokemon.name} is now level {pokemon.level}!"

                    data = self.bot.data.get_species_by_id(pokemon.species_id)
                    if pokemon.level >= data['evolution_level']:
                        oldname = pokemon.name
                        pokemon.species_id = data['evolution'] 
                        embed.add_field(name="Whats this?", value=f"Your {oldname} evolved into {pokemon.name}!")

                    await message.channel.send(embed=embed)



                await self.bot.db.update_pokemon_by_idx(message.author, user.selected, dict(species_id=pokemon.species_id, xp=pokemon.xp, level=pokemon.level), connection=conn)
                
                pokemon.xp_needed

    @commands.Cog.listener("on_message")
    async def spawning(self, message):
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        if cd := self.cooldown.get(message.author.id):
            if time.perf_counter() - cd <= 0.5:
                return
        self.cooldown[message.author.id] = time.perf_counter()

        self.spawns[message.channel.id]["count"] += 1
        if (
            self.spawns[message.channel.id]["count"]
            >= self.spawns[message.channel.id]["goal"]
        ):
            await self.spawn_pokemon(message.channel)

        await self.calculate_xp(message)


def setup(bot):
    bot.add_cog(Spawning(bot))
