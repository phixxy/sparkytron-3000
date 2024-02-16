import logging
import os
import discord
from discord.ext import commands


class OnJoin(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("bot")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = self.bot.get_channel(346102473993355267)
        await channel.send(f"{member.mention} WHO??? :thinking_face:")
        self.logger.info(f"Member {member.name} joined")

async def setup(bot):
    await bot.add_cog(OnJoin(bot))