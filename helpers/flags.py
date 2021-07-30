from discord.ext import commands

class PosixFlags(commands.FlagConverter, prefix="--", delimiter=" "):
    ...
