import random
from discord.ext import commands
import discord

class Waifu(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.url = "https://api.waifu.im/search"

    async def get_waifu(self, tags):
        print(tags)
        params = {
            'included_tags': tags,
            'height': '>=1000'
        }
        async with self.bot.http_session.get(self.url,  params=params) as resp:
                resp_data = await resp.json()
        try:
            image = random.choice(resp_data['images'])
            return image['url']
        except:
            if resp_data['detail'] == "No image found matching the criteria given.":
                return "No image found matching the criteria given."
            else:
                return "Something went wrong"

    @commands.command()
    async def waifu(self, ctx, nsfw=""):
        if nsfw.lower() == "nsfw":
            tag = random.choice(["ero", "ass", "hentai", "milf", "oral", "paizuri", "ecchi"])
        else:
            tag = random.choice(["waifu", "maid", "uniform"])
        image_url = await self.get_waifu(tag)
        if ctx.channel.type == discord.ChannelType["private"]:
            await ctx.send(image_url)
        elif not ctx.channel.is_nsfw() and nsfw.lower() == "nsfw":
            await ctx.send("Cannot post NSFW images in this channel.")
        else:
            await ctx.send(image_url)
            

async def setup(bot):
    try:
        await bot.add_cog(Waifu(bot))
        print("Successfully added Waifu Cog")
    except:
        print("Failed to load Waifu Cog")