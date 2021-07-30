import discord

class Embed(discord.Embed):
    def __init__(self, **kwargs):
        kwargs.setdefault("color", 0x9550F3)
        super().__init__(**kwargs)
