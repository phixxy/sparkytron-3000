import discord
from discord.ext import commands, tasks
from discord.utils import get
import shutil
import json
import time
import os
from dotenv import load_dotenv
import aiohttp

#Stable Diffusion
#Set this env variable to http://host:port or "disabled"
#os.getenv('stablediffusion_url')

#env vars START
load_dotenv()

imgflip_username = os.getenv('imgflip_username')
imgflip_password = os.getenv('imgflip_password')
discord_token    = os.getenv('discord_token')
ftp_server = os.getenv('ftp_server')
ftp_username = os.getenv('ftp_username')
ftp_password = os.getenv('ftp_password')
ftp_public_html = os.getenv('ftp_public_html')

#env vars END

#discord setup START
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
#discord setup END

    
async def folder_setup():
    # Only tmp, extensions and data are supported, all other folders only exist for backwards compatibility and will be removed soon!
    folder_names = ["tmp", "extensions", "data", "channels","channels/config", "channels/logs"]
    for folder_name in folder_names:
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)
    return folder_names
            
async def delete_all_files(path, safe_folders=None):
    for filename in os.listdir(path):
        if os.path.isdir(path+filename) and not path+filename in safe_folders:
            shutil.rmtree(path+filename)
        elif os.path.isfile(path+filename):
            os.remove(path+filename)

            
@tasks.loop(seconds=1)  # Run the task every second
async def task_loop():
    current_time = time.localtime()
    #Run daily tasks
    if current_time.tm_hour == 0 and current_time.tm_min == 0 and current_time.tm_sec == 0:
        try:
            await delete_all_files("tmp/")
        except Exception as error:
            print("Failed to delete_all_files")
            
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
    folders_made = await folder_setup()
    await delete_all_files("tmp/", folders_made)
    # Import plugins from extensions folder
    for plugin_file in os.listdir('extensions/'):
        if plugin_file[0] != '_' and plugin_file[-3:] == '.py':
            await bot.load_extension(f'extensions.{plugin_file[:-3]}')
    print('We have logged in as {0.user}'.format(bot))
    task_loop.start()


@bot.event
async def on_message(ctx):
    # Don't allow commands in DMs for now
    if ctx.channel.type.value != 0 and ctx.author.id != 242018983241318410:
        #This used to notify the user it cannot respond in this channel, but that spammed threads
        return
    
    await bot.process_commands(ctx)

bot.run(discord_token)
