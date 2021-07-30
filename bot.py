import discord
import copy
from discord.ext import commands, store_true
from data.manager import DataManager
import logging
import sys
import asyncpg
import re


class Pokeland(store_true.StoreTrueMixin, commands.Bot):
    """The custom subclass for the bot"""

    def __init__(self, config=None):
        if not config:
            self.config = __import__("config").config

        self.logger = logging.getLogger("discord")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.data = DataManager()

        super().__init__(command_prefix=self.config.prefix)

        self.loop.run_until_complete(self.setup())

    @property
    def db(self):
        return self.get_cog("Database")

    async def get_context(self, message, cls=None):
        cls = cls or self.context
        return await super().get_context(message, cls=cls)

    async def setup(self):
        self.connection = await asyncpg.create_pool(self.config.db_string)
        for extension in self.config.extensions:
            self.load_extension(extension)

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user}")

    def run(self):
        super().run(self.config.token)
