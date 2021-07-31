import discord


class Embed(discord.Embed):
    def __init__(self, **kwargs):
        kwargs.setdefault("color", 0x9550F3)
        super().__init__(**kwargs)

    def compact_image(self, guild,  url):
        if guild.compact:
            self.set_thumbnail(url=url)
        else:
            self.set_image(url=url)
