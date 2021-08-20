import asyncpg
import random
from helpers import constants, models
from collections import defaultdict
from discord.ext import commands


class Database(commands.Cog):
    """The cog for interfacting with the database"""

    def __init__(self, bot):
        self.bot = bot
        self.connection = bot.connection

    def random_ivs(self):
        return [random.randint(1, 31) for i in range(6)]

    def get_id_from_object(self, object):
        if isinstance(object, int):
            return object

        if hasattr(object, "id"):
            return object.id

        if isinstance(object, (dict, asyncpg.Record)):
            return object["id"]

        return None

    def format_query_from_flags(self, flags, start=4):
        filters = defaultdict(list)
        if flags and flags.name:
            filters["species_id"].append(
                self.bot.data.get_species_by_name(flags.name)["species_id"]
            )
        if flags and flags.level:
            filters["level"].append(flags.level)
        if flags and flags.legendary:
            filters["in_species_id"].append(list(self.bot.data.legendary.keys()))
        if flags and flags.mythical:
            filters["in_species_id"].append(list(self.bot.data.mythical.keys()))
        if flags and flags.ultrabeast:
            filters["in_species_id"].append(list(self.bot.data.ultra_beast.keys()))
        if flags and flags.fav:
            filters["favorite"].append(True)

        if filters:
            query, args = self.bot.db.format_query_list(filters, _or=False, start=start)
            query = f"AND ({query})"
        else:
            query = ""
            args = []

        print(query)
        return query, args

    def format_query(self, update, start=2):
        query = ", ".join(
            (f"{c[3:]} = any(${i}::int[])" if c.startswith("in_") else f"{c} = ${i}")
            for i, c in enumerate(update, start)
        )
        args = []
        for item in update:
            args.append(update[item])

        return query, args

    def format_query_list(self, update, *, _or=False, start=2):
        builder = []
        args = []
        idx = start
        for cs in update:
            for c in update[cs]:
                builder.append(
                    f"{cs[3:]} = any(${idx}::int[])"
                    if cs.startswith("in_")
                    else f"{cs} = ${idx}"
                )
                idx += 1
                args.append(c)

        return (" OR " if _or else " AND ").join(builder), args

    async def get_dex(self, id, *, connection=None):
        connection = connection or self.connection
        id = self.get_id_from_object(id)
        entries = await connection.fetch("SELECT * FROM dex WHERE user_id = $1", id)
        if not entries:
            return {}
        return {
            entry["species_id"]: models.DexEntry(*(entry.values())) for entry in entries
        }

    async def get_user(self, id, *, connection=None):
        connection = connection or self.connection
        id = self.get_id_from_object(id)
        user = await connection.fetchrow("SELECT * FROM users WHERE id = $1", id)
        if not user:
            return None
        return models.User(*(user.values()))

    async def get_guild(self, id, *, connection=None):
        connection = connection or self.connection
        id = self.get_id_from_object(id)
        guild = await connection.fetchrow("SELECT * FROM guilds WHERE id = $1", id)
        if not guild:
            return None
        return models.Guild(*(guild.values()))

    async def get_channel(self, id, *, connection=None):
        connection = connection or self.connection
        id = self.get_id_from_object(id)
        channel = await connection.fetchrow("SELECT * FROM channels WHERE id = $1", id)
        if not channel:
            return None
        return models.Channel(*(channel.values()))

    async def get_pokemon_by_idx(self, user_id, idx, *, connection=None):
        connection = connection or self.connection
        user_id = self.get_id_from_object(user_id)
        return await connection.fetchrow(
            "SELECT * FROM pokemon WHERE user_id = $1 AND idx = $2 AND market_price is NULL", user_id, idx
        )

    async def update_pokemon_by_idx(self, user_id, idx, update, *, connection=None):
        connection = connection or self.connection
        user_id = self.get_id_from_object(user_id)
        query, args = self.format_query(update, 3)
        await connection.execute(
            f"UPDATE pokemon SET {query} WHERE user_id = $1 AND idx = $2",
            *([user_id, idx] + args),
        )

    async def update_selected_pokemon(self, user_id, update, *, connection=None):
        connection = connection or self.connection
        user_id = self.get_id_from_object(user_id)
        selected = await connection.fetchval(
            "SELECT selected FROM users WHERE id = $1", user_id
        )
        await self.update_pokemon_by_idx(
            user_id, selected, update, connection=connection
        )

    async def get_next_idx(self, user_id, *, connection=None):
        connection = connection or self.connection
        user_id = self.get_id_from_object(user_id)
        return (
            await connection.fetchval(
                "SELECT idx+1 FROM pokemon WHERE user_id = $1 ORDER BY idx DESC LIMIT 1",
                user_id,
            )
        ) or 1

    async def insert_pokemon(self, user, species_id, *, shiny=False, connection=None):
        id = self.get_id_from_object(user)
        connection = connection or self.connection

        query = f"INSERT INTO pokemon(user_id, idx, species_id, level, xp, nature, shiny, hp_iv, atk_iv, def_iv, spatk_iv, spdef_iv, spd_iv, moves) VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14) RETURNING *"
        values = [
            id,
            await self.get_next_idx(id, connection=connection),
            species_id,
            random.randint(1, 25),
            0,
            random.choice(constants.NATURES),
            shiny,
            *self.random_ivs(),
            ["Tackle"] * 4,
        ]
        return models.Pokemon(await connection.fetchrow(query, *values), self.bot.data)

    async def register(self, id, *, connection=None):
        connection = connection or self.connection
        id = self.get_id_from_object(id)
        try:
            await self.connection.execute(
                "INSERT INTO users(id, selected, bal, redeem) VALUES ($1, $2, $3, $4)",
                id,
                1,
                5,
                0,
            )
        except asyncpg.UniqueViolationError:
            return False

        return True


def setup(bot):
    bot.add_cog(Database(bot))
