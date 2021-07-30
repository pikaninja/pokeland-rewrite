import asyncpg
import random
from helpers import constants, models
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

    def format_quary(self, update, start=2):
        quary = ", ".join(f"{c} = ${i}" for i, c in enumerate(update, start))
        args = []
        for item in update:
            args.append(update[item])

        return quary, args

    async def get_user(self, id, *, connection=None):
        connection = connection or self.connection
        id = self.get_id_from_object(id)
        return models.User(
            *(
                await connection.fetchrow("SELECT * FROM users WHERE id = $1", id)
            ).values()
        )

    async def get_pokemon_by_idx(self, user_id, idx, *, connection=None):
        connection = connection or self.connection
        user_id = self.get_id_from_object(user_id)
        return await connection.fetchrow(
            "SELECT * FROM pokemon WHERE user_id = $1 AND idx = $2", user_id, idx
        )

    async def update_pokemon_by_idx(self, user_id, idx, update, *, connection=None):
        connection = connection or self.connection
        user_id = self.get_id_from_object(user_id)
        quary, args = self.format_quary(update, 3)
        await connection.execute(
            f"UPDATE pokemon SET {quary} WHERE user_id = $1 AND idx = $2",
            *([user_id, id] + args),
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

        quary = f"INSERT INTO pokemon(user_id, idx, species_id, level, xp, nature, shiny, hp_iv, atk_iv, def_iv, spatk_iv, spdef_iv, spd_iv, moves) VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14) RETURNING *"
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
        return models.Pokemon(await connection.fetchrow(quary, *values), self.bot.data)

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
