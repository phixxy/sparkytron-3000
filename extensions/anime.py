import random
from discord.ext import commands
import discord

class Anime(commands.Cog):

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

    async def get_anime_from_img(self, img_url):
        async with self.bot.http_session.get(f"https://api.trace.moe/search?anilistInfo&url={img_url}") as resp:
            resp_data = await resp.json()
        print(resp_data)
        title = resp_data["result"][0]["anilist"]["title"]
        video = resp_data["result"][0]["video"]
        return title, video

    @commands.command(aliases=["what_anime"])
    async def whatanime(self, ctx):
        if ctx.message.attachments:
            file_url = ctx.message.attachments[0].url
        else:
            try:
                file_url = ctx.message.content.split(" ", maxsplit=2)[1]
            except:
                await ctx.send("No image linked or attached.")
                return
        try:
            titles, video = await self.get_anime_from_img(file_url)
        except:
            ctx.send("An error occurred. Try again by saving and uploading the image.")
        message = ""
        for key in titles:
            message += f"{key}: {titles[key]}\n"
        message += f"Scene: {video}"
        await ctx.send(message)



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
        await bot.add_cog(Anime(bot))
        print("Successfully added Anime Cog")
    except:
        print("Failed to load Anime Cog")