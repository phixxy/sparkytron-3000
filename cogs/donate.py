import logging
import os
import time
import matplotlib.pyplot as plt
import discord
from discord.ext import commands


class Donate(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.admin_id = 242018983241318410
        self.donation_link = "https://patreon.com/phixxy"
        self.data_dir = "data/donate/"
        self.donor_file = "data/donate/supporters.txt"
        self.folder_setup()
        self.logger = logging.getLogger("bot")

    def folder_setup(self):
        try:
            if not os.path.exists(self.data_dir):
                os.mkdir(self.data_dir)
        except:
            self.logger.exception("Donate failed to make directories")

    @commands.command(
        description="Donate", 
        help="Get information on how to donate to support this bot.", 
        brief="Donation info",
        ) 
    async def donate(self, ctx):
        await ctx.send(f"If you would like to support the future of this bot please consider donating here: {self.donation_link}")

    @commands.command()
    async def add_supporter(self, ctx, username: str):
        if ctx.author.id != self.admin_id:
            return
        with open(self.donor_file, 'a') as f:
            f.write(f"{username}\n")
        await ctx.send(f"Added {username} to supporters")

    @commands.command()
    async def remove_supporter(self, ctx, username: str):
        if ctx.author.id != self.admin_id:
            return
        with open(self.donor_file, 'r') as f:
            supporters = f.readlines()
        with open(self.donor_file, 'w') as f:
            for line in supporters:
                if line!= username:
                    f.write(line)
        await ctx.send(f"Removed {username} from supporters")

    @commands.command(
        description="Supporters", 
        help="Get information on who supports this bot.", 
        brief="Supporter info",
        aliases = ["supporter"]
        ) 
    async def supporters(self, ctx):
        with open(self.donor_file, 'r') as f:
            supporters = f.readlines()
        message = "Thank you to the following supporters:\n"
        for line in supporters:
            message += line

        await ctx.send(message)


async def setup(bot):
    await bot.add_cog(Donate(bot))