import time
import os
import logging
import aiohttp
import discord
from discord.ext import commands

class TextToSpeech(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.working_dir = "tmp/tts/"
        self.data_dir = "data/tts/"
        self.folder_setup()
        self.http_session = self.create_aiohttp_session()
        self.logger = logging.getLogger("bot")

    def create_aiohttp_session(self):
        return aiohttp.ClientSession()

    def folder_setup(self):
        try:
            if not os.path.exists(self.working_dir):
                os.mkdir(self.working_dir)
            if not os.path.exists(self.data_dir):
                os.mkdir(self.data_dir)
        except:
            self.logger.exception("TextToSpeech failed to make directories")

    async def text_to_speech(self, prompt):
        CHUNK_SIZE = 1024
        url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
        api_key = os.getenv("eleven_labs")
        headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
        }

        data = {
        "text": prompt,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
        }
        filename = f"{time.time_ns()}.mp3"
        filepath = f"{self.data_dir}{filename}"
        response = await self.http_session.post(url, json=data, headers=headers)
        with open(filepath, 'wb') as f:
            async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
        return filepath
    
    async def open_text_to_speech(self, prompt):
        CHUNK_SIZE = 1024
        url = "https://api.openai.com/v1/audio/speech"
        api_key = os.getenv("openai.api_key")
        headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
        }

        data = {
        "input": prompt,
        "model": "tts-1",
        "voice": "alloy"
        }
        filename = f"{time.time_ns()}.mp3"
        filepath = f"{self.data_dir}{filename}"
        response = await self.http_session.post(url, json=data, headers=headers)
        with open(filepath, 'wb') as f:
            async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
        return filepath


    
    def get_prompt_from_ctx(self, ctx):
        try:
            prompt = ctx.message.content.split(" ", maxsplit=1)[1]
            prompt = ' '.join(list(filter(lambda x: '=' not in x,prompt.split(' '))))
            return prompt
        except:
            return None
    
    @commands.command()
    async def tts(self, ctx):
        prompt = self.get_prompt_from_ctx(ctx)
        if prompt is None:
            await ctx.send("Please provide a prompt")
            return
        else:
            await ctx.send("Generating...")
        try:
            filepath = await self.text_to_speech(prompt)
            await ctx.send(file=discord.File(filepath))
        except:
            await ctx.send("Error in tts")
            self.logger.exception("Error in tts")

    @commands.command()
    async def opentts(self, ctx):
        prompt = self.get_prompt_from_ctx(ctx)
        if prompt is None:
            await ctx.send("Please provide a prompt")
            return
        else:
            await ctx.send("Generating...")
        try:
            filepath = await self.open_text_to_speech(prompt)
            await ctx.send(file=discord.File(filepath))
        except:
            await ctx.send("Error in tts")
            self.logger.exception("Error in tts")

async def setup(bot):
    await bot.add_cog(TextToSpeech(bot))