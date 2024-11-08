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
        author_id = str(ctx.author.id)
        try:
            xp_data = read_xp_file(self)
            if author_id in xp_data:
                await ctx.send(f"You have {xp_data[author_id]} XP")
            else:
                await ctx.send("You have 0 XP")
        except:
            await ctx.send("Error getting XP")

    @commands.command()
    async def show_json(self, ctx):
        with open(os.path.join(self.data_dir, "xp.json"), "r") as xp_file:
            xp_data = json.load(xp_file)
        await ctx.send(xp_data)
            

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            author_id = str(message.author.id)
            if message.author.bot:
                return
            else:
                xp_data = read_xp_file(self)
                if author_id in xp_data:
                    xp_data[author_id] += 1
                else:
                    xp_data[author_id] = 1

                with open(os.path.join(self.data_dir, "xp.json"), "w") as xp_file:
                    json.dump(xp_data, xp_file)
        except Exception as e:
            self.logger.error(f"Error adding XP: {e}")

def read_xp_file(self):
    try:
        with open(os.path.join(self.data_dir, "xp.json"), "r") as xp_file:
            xp_data = json.load(xp_file)
        return xp_data
    except Exception as e:
        self.logger.error(f"No XP file found. Returning empty json object: {e}")
        return {}
                

async def setup(bot):
    await bot.add_cog(MessageXP(bot))