import logging
import os
import discord
from discord.ext import commands
import wakeonlan


class WakeOnLan(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.admin_id = 242018983241318410
        self.logger = logging.getLogger("bot")
        self.mac_address = "9C-6B-00-38-08-8D"

    def wake_on_lan(self, mac_address):
        self.logger.info(f"WakeOnLan: Waking up {mac_address}")
        wakeonlan.send_magic_packet(mac_address)

    def sleep_on_lan(self, mac_address):
        self.logger.info(f"WakeOnLan: Sleeping {mac_address}")
        wakeonlan.send_magic_packet(mac_address, magic_packet="000000000000")

    @commands.command()
    async def wake(self, ctx):
        if ctx.author.id != self.admin_id:
            return
        self.wake_on_lan(self.mac_address)
        await ctx.send(f"Waking up !imagine server")


async def setup(bot):
    await bot.add_cog(WakeOnLan(bot))