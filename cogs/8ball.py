import logging
import random
import matplotlib.pyplot as plt
import discord
from discord.ext import commands


class MagicBall(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("bot")

    @commands.command(
        description="Magic ball",
        help="Ask the magic ball a question.",
        brief="Ask the magic ball a question.",
        aliases=["8ball"]
        )
    async def magicball(self, ctx, *, question):
        responses = ["It is certain.", "It is decidedly so.", "Without a doubt.", "Yes - definitely.", "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.", "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.", "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."]
        response = random.choice(responses)
        await ctx.reply(response)
        self.logger.info(f"Magicball command called by {ctx.author.name}")

async def setup(bot):
    await bot.add_cog(MagicBall(bot))