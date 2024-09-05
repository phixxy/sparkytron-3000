import os
import subprocess

from discord.ext import commands, tasks
from cogs.base_cog.bot_base_cog import BotBaseCog

class YoutubeDL(BotBaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        self.setup(__class__.__name__)

    @commands.command()
    async def youtubedl(self, ctx):
        try:
            url = ctx.message.content.split(" ", 1)[1]
            url = '"' + url + '"'
            video_or_audio = ctx.message.content.split(" ", 2)[2]
            process = subprocess.Popen(["python3", "data/ytdl/youtubedl.py", url, video_or_audio])
            process.wait()
            await ctx.send(process.stdout)
            await ctx.send(f"Downloading {video_or_audio} from {url}...", embeds=None)
        except:
            await ctx.send("Usage: !youtubedl <url> <video|audio>")
            
    #create a task
    @tasks.loop(seconds=10)
    async def check_for_downloads(self):
        for file in os.listdir("data/ytdl"):
            if file.endswith(".txt"):
                await self.bot.get_channel(544408659174883328).send(f"{file[:-4]}")
                os.remove(f"data/ytdl/{file}")

async def setup(bot):
    await bot.add_cog(YoutubeDL(bot))