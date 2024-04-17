import logging
import os
import asyncssh
import discord
from discord.ext import commands
import wakeonlan


class WakeOnLan(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.admin_id = 242018983241318410
        self.logger = logging.getLogger("bot")
        self.mac_address = "9C-6B-00-38-08-8D"
        self.stable_diffusion_ip = os.getenv("stable_diffusion_ip")
        self.stable_diffusion_login = os.getenv("stable_diffusion_login")
        self.stable_diffusion_password = os.getenv("stable_diffusion_password")

    def wake_on_lan(self, mac_address):
        self.logger.info(f"WakeOnLan: Waking up {mac_address}")
        wakeonlan.send_magic_packet(mac_address)

    @commands.command()
    async def wake(self, ctx):
        if ctx.author.id != self.admin_id:
            return
        self.wake_on_lan(self.mac_address)
        await ctx.send(f"Waking up !imagine server")

    @commands.command(
        description="shutdown imagine server", 
        help="shutdown imagine server",
        brief="shutdown imagine server",
        hidden=True
        )           
    async def sleep(self, ctx, amount=5):
        if ctx.author.id == self.admin_id:
            #use ssh to login and shutdown
            async with asyncssh.connect(
                self.stable_diffusion_ip,
                username=self.stable_diffusion_login,
                password=self.stable_diffusion_password,
            ) as ssh_client:
                try:
                    result = await ssh_client.run("shutdown /s")
                    await ctx.send(result.stdout)
                    #await ssh_client.run("sudo shutdown -h now")
                except:
                    self.logger.exception("WakeOnLan: Sleeping failed")
                    await ctx.send("Sleeping failed")


async def setup(bot):
    await bot.add_cog(WakeOnLan(bot))