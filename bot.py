import discord
import copy
from discord.ext import commands, store_true
from data.manager import DataManager
import logging
import sys
import asyncpg
import re

ignore = ['name', 'levelno', 'pathname', 'filename', 'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated', 'thread', 'threadName', 'processName', 'process']

class LoggingFormat(logging.Formatter):
    def format(self, record):
        arguments = {
            key: value
            for key, value in record.__dict__.items()
            if key not in ignore
        }
        return ", ".join(f"{key}={value}" for key, value in arguments.items())

def prefix(bot, message):
    return bot.get_cog("Meta").get_prefix(message.channel.guild)

class Pokeland(store_true.StoreTrueMixin, commands.Bot):
    """The custom subclass for the bot"""

    def __init__(self, config=None):
        if not config:
            self.config = __import__("config").config

        self.logger = logging.getLogger("discord")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(LoggingFormat())
        self.logger.addHandler(handler)
        self.data = DataManager()

        super().__init__(command_prefix=prefix)

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

    async def on_command(self, ctx):
        self.logger.info(
            "Command Ran",
            extra = {
                "id": ctx.author.id,
                "tag": str(ctx.author),
                "guild_id": ctx.guild.id,
                "guild": str(ctx.guild),
                "content": ctx.message.content
            }
        )

    def run(self):
        super().run(self.config.token)
