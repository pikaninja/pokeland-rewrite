import asyncpg
from discord.ext import commands

class Database(commands.Cog):
    """The cog for interfacting with the database"""
    def __init__(self, bot):
        self.bot = bot
        self.connection = self.bot.loop.create_task(asyncpg.create_pool(bot.config.db_string))

def setup(bot):
    bot.add_cog(Database(bot))

    
