import discord
from discord.ext import commands, tasks
import shutil
import time
import os
from dotenv import load_dotenv
import aiohttp
import src.logger as logger

load_dotenv()
discord_token = os.getenv('discord_token')

logger = logger.logging.getLogger("bot")

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def folder_setup():
    try:
        folder_names = ["tmp", "extensions", "data"]
        for folder_name in folder_names:
            if not os.path.exists(folder_name):
                os.mkdir(folder_name)
        return folder_names
    except Exception as e:
        logger.error(f"Error setting up folders: {e}")

async def delete_all_files(path):
    try:
        for filename in os.listdir(path):
            if os.path.isdir(path+filename):
                shutil.rmtree(path+filename)
            elif os.path.isfile(path+filename):
                os.remove(path+filename)
    except Exception as e:
        logger.error(f"Error deleting files: {e}")

@tasks.loop(seconds=1)  # Run the task every second
async def task_loop():
    try:
        current_time = time.localtime()
        #Run daily tasks
        if current_time.tm_hour == 0 and current_time.tm_min == 0 and current_time.tm_sec == 0:
            await delete_all_files("tmp/")
            logger.info("Deleted tmp/ files.")
    except Exception as e:
        logger.error(f"Error in task loop: {e}")

async def create_session():
    return aiohttp.ClientSession()

async def close_session(http_session):
    await http_session.close()
            
@bot.event
async def on_connect():
    bot.http_session = await create_session()

@bot.event    
async def on_resumed():
    bot.http_session = await create_session()

@bot.event
async def on_disconnect():
    await close_session(bot.http_session)
            
@bot.event
async def on_ready():
    try:
        bot.logger = logger
        await delete_all_files("tmp/")
        # Import plugins from extensions folder
        for plugin_file in os.listdir('extensions/'):
            if plugin_file[0] != '_' and plugin_file[-3:] == '.py':
                await bot.load_extension(f'extensions.{plugin_file[:-3]}')
        logger.info('We have logged in as {0.user}'.format(bot))
        task_loop.start()
    except Exception as e:
        logger.error(f"Error in on_ready: {e}")
        raise

@bot.event
async def on_message(ctx):
    try:
        await bot.process_commands(ctx)
    except commands.CommandNotFound:
        pass
    except Exception as e:
        logger.error(f"Error processing commands: {e}")

try:
    bot.run(discord_token, root_logger=True) 
except Exception as e:
    logger.critical(f"Fatal error running bot: {e}")
