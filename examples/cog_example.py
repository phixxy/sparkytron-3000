from discord.ext import commands
from cogs.base_cog.bot_base_cog import BotBaseCog

class Ping(BotBaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        self.setup(__class__.__name__)

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("pong")
        self.logger.info(f"Ping command called by {ctx.author.name}")

async def setup(bot):
    await bot.add_cog(Ping(bot))