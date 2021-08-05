from helpers import constants
from discord.ext import commands

class Economy(commands.Cog):
    """Commands related to balance and redeems"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases = ("bal",))
    async def balance(self, ctx):
        """View your current balance"""
        user = await self.bot.db.get_user(ctx.author)
        embed = constants.Embed(
            title = f"{ctx.author.display_name}'s balance",
            description = f"{user.bal:,} credits"
        )
        embed.set_thumbnail(
            url="https://images-ext-2.discordapp.net/external/xlEcYc2ErW6-vD7-nHbk3pv2u4sNwjDVx3jFEL6w9fc/https/emojipedia-us.s3.amazonaws.com/thumbs/120/emoji-one/104/money-bag_1f4b0.png"
        )
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Economy(bot))
