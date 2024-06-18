import logging
import discord
from discord.ext import commands
import meshtastic
import meshtastic.serial_interface

class Meshtastic(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("bot")
        self.interface = meshtastic.serial_interface.SerialInterface()

    @commands.command(
        description="Meshtastic",
        help="Ask the magic ball a question.",
        brief="Ask the magic ball a question.",
        aliases=["mesh"]
        )
    async def mesh(self, ctx, *args):
        message = " ".join(args)
        self.interface.sendText(message)
        self.logger.info(f"Meshtastic command called by {ctx.author.name}")

async def setup(bot):
    await bot.add_cog(Meshtastic(bot))