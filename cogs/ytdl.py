import os
import subprocess
import asyncio

from discord.ext import commands, tasks
from cogs.base_cog.bot_base_cog import BotBaseCog

class YoutubeDL(BotBaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        self.setup(__class__.__name__)
        self.check_for_downloads.start()

    '''    @commands.command()
    async def youtubedl(self, ctx):
        try:
            # Expecting the command format to be !youtubedl <url> <video|audio>
            parts = ctx.message.content.split(" ")
            if len(parts) < 3:
                await ctx.send("Usage: !youtubedl <url> <video|audio>")
                return

            url = parts[1]
            video_or_audio = parts[2]
            
            # Run the subprocess
            process = subprocess.Popen(
                ["python3", "youtubedl.py", url, video_or_audio],
                cwd="data/ytdl",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for the process to complete and read the output
            stdout, stderr = process.communicate()

            # Send the output back to the user
            #await ctx.send(f"std out: {stdout.decode('utf-8')}") if stdout else await ctx.send("No stdout output")
            #await ctx.send(f"std err: {stderr.decode('utf-8')}") if stderr else await ctx.send("No stderr output")
            await ctx.send(f"Downloading {video_or_audio} from {url}...", suppress_embeds=True)

        except Exception as e:
            #await ctx.send(f"Error: {e}")
            await ctx.send("Usage: !youtubedl <url> <video|audio>")'''

    @commands.command()
    async def youtubedl(self, ctx):
        try:
            # Expecting the command format to be !youtubedl <url> <video|audio>
            parts = ctx.message.content.split(" ")
            if len(parts) < 3:
                await ctx.send("Usage: !youtubedl <url> <video|audio>")
                return

            url = parts[1]
            video_or_audio = parts[2]
            
            # Create a subprocess
            process = await asyncio.create_subprocess_exec(
                "python3", "youtubedl.py", url, video_or_audio,
                cwd="data/ytdl",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Write a message that the download has started
            await ctx.send(f"Downloading {video_or_audio} from {url}...")

            # Read stdout and stderr (non-blocking)
            stdout, stderr = await process.communicate()

            # Send the output back to the user
            if stdout:
                await ctx.send(f"std out: {stdout.decode('utf-8')}")
            if stderr:
                await ctx.send(f"std err: {stderr.decode('utf-8')}")

        except Exception as e:
            await ctx.send(f"Error: {e}")
                
    #create a task
    @tasks.loop(seconds=10)
    async def check_for_downloads(self):
        for file in os.listdir("data/ytdl"):
            if file.endswith(".txt"):
                with open(f"data/ytdl/{file}", "r") as f:
                    url = f.read()
                await self.bot.get_channel(544408659174883328).send(f"{url}")
                os.remove(f"data/ytdl/{file}")

async def setup(bot):
    await bot.add_cog(YoutubeDL(bot))