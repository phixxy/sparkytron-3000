import os
import discord
from discord.ext import commands
import aiohttp
from dotenv import load_dotenv
import src.logger as logger
import src.utils as utils

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
bot.logger = logger.logger_setup()

async def create_session():
    return aiohttp.ClientSession()

async def close_session(http_session):
    await http_session.close()

async def load_cogs(bot: commands.Bot, cog_path: str) -> None:
    for plugin_file in os.listdir(cog_path):
        if plugin_file[-3:] == '.py':
            try:
                await bot.load_extension(f'extensions.{plugin_file[:-3]}')
                bot.logger.info(f"Successfully loaded plugin {plugin_file}")
            except:
                bot.logger.exception(f"Failed to load plugin {plugin_file}")
            
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
        await utils.delete_all_files("tmp/")
        await utils.folder_setup()
        await load_cogs(bot, 'extensions/')
        bot.logger.info('We have logged in as {0.user}'.format(bot))
    except:
        bot.logger.warning(f"Error in on_ready")

@bot.event
async def on_message(ctx):
    try:
        await bot.process_commands(ctx)
    except commands.CommandNotFound:
        bot.logger.info("Command not found.")
    except discord.ext.commands.errors.CommandNotFound:
        bot.logger.info("Command not found.")
    except Exception as e:
        bot.logger.warning(f"Error processing commands: {e}")
