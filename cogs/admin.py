from discord.ext import commands

class Admin(commands.Cog):
    """Commands for bot administration"""
    @commands.group(case_insensitive=True, invoke_without_command=True)
    async def dev(self, ctx):
        await ctx.send_help(ctx.command)

    @dev.command()
    async def random_spawn(self, ctx):
        await ctx.bot.get_cog("Spawning").spawn_pokemon(ctx.channel)

def setup(bot):
    bot.add_cog(Admin(bot))
    
