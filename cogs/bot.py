import io
import discord
import traceback
from helpers import constants
from discord.ext import commands


class Bot(commands.Cog):
    """Various bot features"""
    def __init__(self, bot):
        self.bot = bot
        self.cd = commands.CooldownMapping.from_cooldown(5, 3, commands.BucketType.user)

    async def bot_check_once(self, ctx):
        bucket = self.cd.get_bucket(ctx.message)
        if retry_after := bucket.update_rate_limit():
            raise commands.CommandOnCooldown(bucket, retry_after, commands.BucketType.user)

        return True


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

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

        elif isinstance(
            error,
            (
                commands.BadArgument,
                commands.UserInputError,
                commands.CheckFailure,
                discord.HTTPException,
                commands.InvalidEndOfQuotedStringError,
                commands.ExpectedClosingQuoteError,
            ),
        ):
            return await ctx.send(str(error))

        else:
            etype = type(error)
            trace = error.__traceback__

            # 'traceback' is the stdlib module, `import traceback`.
            lines = traceback.format_exception(etype, error, trace)

            # format_exception returns a list with line breaks embedded in the lines, so let's just stitch the elements together
            traceback_text = "".join(lines)

            text = f"```{traceback_text}```"
            if len(text) >= 2000:
                msg = await self.bot.get_channel(
                    self.bot.config.error_log_channel_id
                ).send(
                    file=discord.File(io.BytesIO(text.encode()), filename="error.py")
                )
            else:
                msg = await self.bot.get_channel(
                    self.bot.config.error_log_channel_id
                ).send(text)
            self.bot.logger.info("Error Occured", extra={"link": msg.jump_url})
            await ctx.send(
                "Uh-oh! An unexpected error occured! This error has been logged and will be fixed as soon as possible."
            )


def setup(bot):
    bot.add_cog(Bot(bot))
