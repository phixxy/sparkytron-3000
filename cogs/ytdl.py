import os
import subprocess

from discord.ext import commands
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
            output = process.returncode
            await ctx.send(f"Downloaded {video_or_audio} from {url}, output: {output}")
        except:
            await ctx.send("Usage: !youtubedl <url> <video|audio>")

async def setup(bot):
    await bot.add_cog(YoutubeDL(bot))