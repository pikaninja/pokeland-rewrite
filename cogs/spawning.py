import time
import random
import discord

from collections import defaultdict

from discord.ext import commands
from helpers import constants, models, checks


class Spawning(commands.Cog):
    """The category for spawning pokemon"""

    def __init__(self, bot):
        self.bot = bot

        def default_spawn():
            return dict(
                pokemon=None, count=0, goal=random.randint(25, 50), timestamp=None
            )

        self.spawns = defaultdict(default_spawn)
        self.cooldown = {}

    def random_pokemon(self):
        pokemon = list(self.bot.data.data.values())
        pokemon = random.choices(
            pokemon, weights=[x.get("abundance", 0) for x in pokemon], k=1
        )[0]
        return pokemon

    async def spawn_pokemon(
        self, channel, pokemon=None, *, guild=None, connection=None
    ):
        dummy_ctx = discord.Object(id=0)
        dummy_message = discord.Object(id=0)
        dummy_message.channel = channel
        dummy_ctx.message = dummy_message
        self.hint.reset_cooldown(dummy_ctx)
        if not guild:
            guild = await self.bot.db.get_guild(channel.guild, connection=connection)

        if c := await self.bot.db.get_channel(channel):
            if c.spawns_disabled or c.disabled:
                self.spawns[channel.id]["count"] = 0
                return

        pokemon = (
            self.bot.data.get_species_by_name(pokemon)
            if pokemon
            else self.random_pokemon()
        )
        self.spawns[channel.id]["pokemon"] = pokemon
        self.spawns[channel.id]["count"] = 0
        self.spawns[channel.id]["goal"] = random.randint(25, 50)
        self.spawns[channel.id]["timestamp"] = time.perf_counter()
        embed = constants.Embed(
            title="A wild pokemon as appeared!",
            description=f"Guess the pokémon's name and type `{await self.bot.get_cog('Meta').get_prefix(channel.guild)}catch <pokemon>` to catch it!",
        )
        embed.compact_image(guild, url=self.bot.data.image(pokemon["species_id"]))

        await channel.send(embed=embed)

    @commands.command(aliases=("capture",))
    @checks.has_started()
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

        if time.perf_counter() - self.spawns[ctx.channel.id]["timestamp"] < 1:
            self.bot.logger.info(
                "User caught pokemon in under a second",
                extra={
                    "id": ctx.author.id,
                    "tag": str(ctx.author),
                    "guild_id": ctx.guild.id,
                    "guild": ctx.guild,
                    "content": ctx.message.content,
                },
            )

        if self.bot.config.debug:
            await ctx.send(
                f"Pokemon caught in {time.perf_counter() - self.spawns[ctx.channel.id]['timestamp']} seconds"
            )
        self.spawns[ctx.channel.id]["pokemon"] = None

        percentage = 1 / 4096  # in future make changable
        shiny = random.random() <= percentage

        async with self.bot.connection.acquire() as connection:
            async with connection.transaction():
                poke = await self.bot.db.insert_pokemon(
                    ctx.author, pokemon["species_id"], shiny=shiny
                )

                count = await connection.fetchval(
                    "INSERT INTO dex(user_id, species_id, count)"
                    "VALUES($1, $2, 1) ON CONFLICT(user_id, species_id)"
                    "DO UPDATE SET count = dex.count+1"
                    "RETURNING count",
                    ctx.author.id,
                    pokemon["species_id"],
                )

                message = f"Congratulations {ctx.author.mention}! You caught a level {poke.level} {'✨' if shiny else ''}{poke.name}!"
                if count == 1:
                    message += " Added to pokédex. You've recieved 35 credits!"
                    await connection.execute(
                        "UPDATE users SET bal = bal + 35 WHERE id = $1", ctx.author.id
                    )
                elif count in (10, 100, 1000):
                    message += f" You've caught {count} of this pokémon! You've recieved {35*count} credits!"
                    await connection.execute(
                        "UPDATE users SET bal = bal + (35 * $2) WHERE id = $1",
                        ctx.author.id,
                        count,
                    )
        await ctx.send(message)

    @commands.command()
    @commands.cooldown(1, 20, type=commands.BucketType.channel)
    async def hint(self, ctx):
        """View a hint for the currently spawned pokemon"""
        if not self.spawns[ctx.channel.id]["pokemon"]:
            return await ctx.send("Theres no wild pokemon currently!")

        name = self.spawns[ctx.channel.id]["pokemon"]["name"]

        to_display = random.sample(
            range(len(name)), k=random.randint(2, len(name) // 2)
        )
        hint = "".join(
            l if index in to_display else r"\_" for index, l in enumerate(name)
        )
        await ctx.send(f"The wild pokemon is: {hint}")

    async def calculate_xp(self, message, *, connection=None):
        connection = connection or self.bot.db.connection
        user = await self.bot.db.get_user(message.author, connection=connection)
        if not user:
            return
        pokemon = models.Pokemon(
            await self.bot.db.get_pokemon_by_idx(
                message.author, user.selected, connection=connection
            ),
            self.bot.data,
        )
        if pokemon.item == "XP Blocker":
            return
        if pokemon.level == 100:
            return

        xp = random.randint(10, 40)

        pokemon.xp += xp

        if pokemon.xp >= pokemon.xp_needed:
            embed = constants.Embed(
                title=f"Congratulations {message.author.display_name}!"
            )
            while pokemon.xp >= pokemon.xp_needed:
                pokemon.xp -= pokemon.xp_needed
                pokemon.level += 1
            embed.description = f"Your {pokemon.name} is now level {pokemon.level}!"

            data = self.bot.data.get_species_by_id(pokemon.species_id)
            if pokemon.level >= data.get("evolution_level", 101):
                oldname = pokemon.name
                pokemon.species_id = data["evolution"]
                embed.add_field(
                    name="Whats this?",
                    value=f"Your {oldname} evolved into {pokemon.name}!",
                )

            if not user.hide_levelup:
                await message.channel.send(embed=embed)

        await self.bot.db.update_pokemon_by_idx(
            message.author,
            user.selected,
            dict(
                species_id=pokemon.species_id,
                xp=pokemon.xp,
                level=pokemon.level,
            ),
            connection=connection,
        )

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
            async with self.bot.connection.acquire() as connection:
                async with connection.transaction():
                    guild = await self.bot.db.get_guild(
                        message.guild, connection=connection
                    )
                    if not guild or not guild.redirects:
                        channel = message.channel
                    else:
                        channel = message.guild.get_channel(
                            random.choice(guild.redirects)
                        )
                    await self.spawn_pokemon(
                        channel, guild=guild, connection=connection
                    )

        await self.calculate_xp(message)


def setup(bot):
    bot.add_cog(Spawning(bot))
