import os
import aiohttp
from discord.ext import commands
import logging

class BotBaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.http_session = self.create_aiohttp_session()
        self.logger = logging.getLogger("bot")

    def setup(self, name):
        self.cog_name = name.lower()
        self.working_dir = f"tmp/{self.cog_name}"
        self.data_dir = f"data/{self.cog_name}"
        self.folder_setup()

    def create_aiohttp_session(self):
        return aiohttp.ClientSession()
    
    def folder_setup(self) -> None:
        try:
            if not os.path.exists(self.working_dir):
                os.mkdir(self.working_dir)
            if not os.path.exists(self.data_dir):
                os.mkdir(self.data_dir)
        except:
            self.logger.exception(f"{self.class_name} failed to make directories")