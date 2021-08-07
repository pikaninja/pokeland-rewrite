from helpers import constants, checks, converters
from discord.ext import commands


class Economy(commands.Cog):
    """Commands related to balance and redeems"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=("bal",))
    @checks.has_started()
    async def balance(self, ctx):
        """View your current balance"""
        user = await self.bot.db.get_user(ctx.author)
        embed = constants.Embed(
            title=f"{ctx.author.display_name}'s balance",
            description=f"{user.bal:,} credits",
        )
        embed.set_thumbnail(
            url="https://images-ext-2.discordapp.net/external/xlEcYc2ErW6-vD7-nHbk3pv2u4sNwjDVx3jFEL6w9fc/https/emojipedia-us.s3.amazonaws.com/thumbs/120/emoji-one/104/money-bag_1f4b0.png"
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=("redeems",), usage="<pokemon/credits>")
    @checks.has_started()
    async def redeem(self, ctx, pokemon=None):
        """Redeem credits or a pokemon"""
        # NOTE: This command is so long because of slash commands, we cannot make sub and group commands
        user = await self.bot.db.get_user(ctx.author)
        if pokemon is None:
            embed = constants.Embed(
                title=f"Your Redeems: {user.redeem}",
                description="Redeems are a special type of currency that can be used to get either a pokémon of your choice, or 15,000 credits.",
            )
            embed.add_field(
                name=f"{ctx.prefix}redeem <pokemon>",
                value="Use a redeem to obtain a pokémon of your choice.",
            )
            embed.add_field(
                name=f"{ctx.prefix}redeem credits",
                value="Use a redeem to obtain 15,000 credits,",
            )
            return await ctx.send(embed=embed)

        if user.redeem <= 0:
            return await ctx.send("You don't have any redeems!")

        if pokemon.lower() == "credits":
            await self.bot.connection.execute(
                "UPDATE users SET redeem=redeem-1, bal=bal+15000 WHERE id = $1",
                ctx.author.id,
            )
            await ctx.send("Money added!")
        else:
            pokemon = self.bot.data.get_species_by_name(pokemon)
            if not pokemon:
                return await ctx.send("Thats not a valid pokenmon!")

            async with self.bot.connection.acquire() as connection:
                async with connection.transaction():
                    await self.bot.db.insert_pokemon(
                        ctx.author, pokemon["species_id"], connection=connection
                    )
                    await connection.execute(
                        "UPDATE users SET redeem=redeem-1 WHERE id = $1", ctx.author.id
                    )
            await ctx.send("You have redeemed a pikachu")

    # @commands.command(aliases=("rs", ))
    # @checks.has_started()
    # async def redeemspawn(self, ctx, pokemon: converters.DexConverter):


def setup(bot):
    bot.add_cog(Economy(bot))
