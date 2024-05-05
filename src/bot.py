import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import src.logger
import src.utils as utils

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
logger = src.logger.logger_setup()


async def load_cogs(bot: commands.Bot, cog_path: str) -> None:
    for cog_file in os.listdir(cog_path):
        if cog_file[-3:] == '.py':
            try:
                await bot.load_extension(f'{cog_path[:-1]}.{cog_file[:-3]}')
                logger.info(f"Successfully loaded cog {cog_file}")
            except:
                logger.exception(f"Failed to load cog {cog_file}")
            
@bot.event
async def on_ready():
    try:
        await utils.folder_setup()
        await utils.delete_all_files("tmp/")
        await load_cogs(bot, 'cogs/')
        logger.info('We have logged in as {0.user}'.format(bot))
    except:
        logger.warning(f"Error in on_ready")

@bot.event
async def on_message(ctx):
    if ctx.channel.type == discord.ChannelType.private and ctx.author.id != 242018983241318410:
        return
    if ctx.author.bot:
        return
    try:
        await bot.process_commands(ctx)
    except commands.CommandNotFound:
        logger.info("Command not found.")
    except discord.ext.commands.errors.CommandNotFound:
        logger.info("Command not found.")
    except Exception as e:
        logger.warning(f"Error processing commands: {e}")
