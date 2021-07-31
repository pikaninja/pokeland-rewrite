import discord
import traceback
from helpers import constants, misc
from discord.ext import commands

class Meta(commands.Cog):
    """Commands for bot configuration"""
    def __init__(self, bot):
        self.bot = bot

    async def get_prefix(self, guild):
        guild = await self.bot.db.get_guild(guild.id)
        if not guild:
            return self.bot.config.prefix
        return guild.prefix or self.bot.config.prefix

    @commands.group(invoke_without_command=True, case_insensitive=True)
    async def prefix(self, ctx):
        """The group command for prefix management, use with no subcommand to view current prefix"""
        await ctx.send(f"The current prefix is `{await self.get_prefix(ctx.channel.guild)}` You can also mention me!")
            
    @prefix.command()
    @commands.has_permissions(manage_guild=True)
    async def set(self, ctx, prefix):
        """Set the prefix for the guild to somethign else"""
        await self.bot.connection.execute("INSERT INTO guilds(id, prefix) VALUES($1, $2) ON CONFLICT(id) DO UPDATE SET prefix=$2", ctx.guild.id, prefix)
        await ctx.send(f"Set the server prefix to `{prefix}`")

    @prefix.command()
    @commands.has_permissions(manage_guild=True)
    async def reset(self, ctx, prefix):
        """Reset the prefix to the default prefix"""
        await self.bot.connection.execute("UPDATE guilds SET prefix=$1 WHERE id = $2", None, ctx.guild.id)
        await ctx.send(f"Reset the guild prefix to `{self.bot.config.prefix}`")

    @commands.command()
    async def ping(self, ctx):
        """Pong!"""
        message = await ctx.send("Pong!")
        delay = int(1000 * (message.created_at - ctx.message.created_at).total_seconds())
        
        if await self.bot.is_owner(ctx.author):
            with misc.StopWatch() as s:
                await self.bot.connection.execute("SELECT 1;")

            await message.edit(content=f"Pong! **{delay} ms**. **{s.time*1000:,.2f} ms db ping**, **{int(self.bot.latency*1000)} ms websocket**")

        else:
            await message.edit(content=f"Pong! **{delay} ms**")


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
             return 

        elif isinstance(error, (commands.BadArgument, commands.UserInputError, commands.CheckFailure, discord.HTTPException, commands.InvalidEndOfQuotedStringError, commands.ExpectedClosingQuoteError)):
            return await ctx.send(str(error))

        elif isinstance(error, commands.ConversionError):
            await ctx.send(str(error.original))

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send_help(ctx.command)
        
        elif isinstance(error, commands.CommandOnCooldown):
            return await ctx.message.add_reaction("\N{CLOCK FACE FOUR OCLOCK}")

        elif isinstance(error, commands.MissingPermissions):
            return await ctx.send(
                embed=constants.Embed(
                    color=discord.Color.red(),
                    title=":x: You are missing permissions",
                    description="You need the following permissions to use this command:\n"
                    + "\n".join(error.missing_permissions).replace("_", " "),
                )
            )
        elif isinstance(error, commands.BotMissingPermissions):
            return await ctx.send(
                embed=constants.Embed(
                    color=discord.Color.red(),
                    title=":x: I am missing permissions",
                    description="I need the following permissions to run this command:\n"
                    + "\n".join(error.missing_permissions).replace("_", " "),
                )
            )

        elif isinstance(error, commands.MaxConcurrencyReached):
            return await ctx.send(
                f"This command can only be used `{error.number}` time{'s' if error.number > 1 else ''} per {str(error.per).replace('BucketType.', '')} concurrently"
            )

        else:
            etype = type(error)
            trace = error.__traceback__
            
            # 'traceback' is the stdlib module, `import traceback`.
            lines = traceback.format_exception(etype, error, trace)
            
            # format_exception returns a list with line breaks embedded in the lines, so let's just stitch the elements together
            traceback_text = ''.join(lines)

            await self.bot.get_channel(self.bot.config.error_log_channel_id).send(f"```{traceback_text}```")

def setup(bot):
    bot.add_cog(Meta(bot))


