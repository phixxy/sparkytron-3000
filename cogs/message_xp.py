from discord.ext import commands
import discord
import json
import os
from cogs.base_cog.bot_base_cog import BotBaseCog

class MessageXP(BotBaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        self.setup(__class__.__name__)

    @commands.command()
    async def stats(self, ctx):
        author_id = ctx.author.id
        if not os.path.exists(self.data_dir + "xp.json"):
            create_xp_file(self)
        try:
            with open(self.data_dir + "xp.json", "r") as xp_file:
                xp_data = json.load(xp_file)
                xp_file.close()
            if author_id in xp_data:
                await ctx.send(f"You have {xp_data[author_id]} XP")
            else:
                await ctx.send("You have 0 XP")
        except:
            await ctx.send("Error getting XP")
            

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            author_id = message.author.id
            if message.author.bot:
                return
            else:
                #check if file exists
                if not os.path.exists(os.path.join(self.data_dir, "xp.json")):
                    create_xp_file(self)

                with open(os.path.join(self.data_dir, "xp.json"), "r") as xp_file:
                    xp_data = json.load(xp_file)

                if author_id in xp_data:
                    xp_data[author_id] += 1
                else:
                    xp_data[author_id] = 1

                with open(os.path.join(self.data_dir, "xp.json"), "w") as xp_file:
                    json.dump(xp_data, xp_file)
        except Exception as e:
            self.logger.error(f"Error adding XP: {e}")

def create_xp_file(self):
    with open(os.path.join(self.data_dir, "xp.json"), "w") as xp_file:
        xp_data = {}
        json.dump(xp_data, xp_file)
                

async def setup(bot):
    await bot.add_cog(MessageXP(bot))