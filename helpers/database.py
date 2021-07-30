import asyncpg
from discord.ext import commands

class Database(commands.Cog):
    """The cog for interfacting with the database"""
    def __init__(self, bot):
        self.bot = bot
        self.connection = bot.connection

    def get_id_from_object(self, object):
        if isinstance(object, int):
            return object

        if hasattr(object, "id"):
            return object.id

        if isinstance(object, dict):
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
        return await connection.fetchrow("SELECT * FROM users WHERE id = $1", id)

    async def get_pokemon_by_idx(self, user_id, idx, *, connection=None):
        connection = connection or self.connection
        id = self.get_id_from_object(user_id)
        return await connection.fetchrow("SELECT * FROM pokemon WHERE user_id = $1 AND idx = $2", user_id, idx)

    async def update_pokemon_by_idx(self, user_id, idx, update, *, connection=None):
        connection = connection or self.connection
        id = self.get_id_from_object(user_id)
        quary, args = self.format_quary(update, 3)
        await connection.execute(f"UPDATE pokemon SET {quary} WHERE user_id = $1 AND idx = $2", [user_id, id] + args)

        

def setup(bot):
    bot.add_cog(Database(bot))

    
