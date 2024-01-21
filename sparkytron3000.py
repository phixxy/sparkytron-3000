import discord
from discord.ext import commands, tasks
from discord.utils import get
import shutil
import json
import random
import time
import os
import asyncio
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
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
#discord setup END


    
async def handle_error(error):
    print(error)
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log_line = current_time + ': ' + str(error) + '\n'
    with open("data/error_log.txt", 'a') as f:
        f.write(log_line)
    return error

def create_channel_config(filepath):
    config_dict = {
        "personality":"average",
        "channel_topic":"casual",
        "chat_enabled":False,
        "commands_enabled":True,
        "chat_history_len":5,
        "look_at_images":False,
        "react_to_msgs":False,
        "ftp_enabled":False
    }

    with open(filepath,"w") as f:
        json.dump(config_dict,f)
    print("Wrote config variables to file.")

async def get_channel_config(channel_id):
    filepath = "channels/config/{0}.json".format(str(channel_id))
    if not os.path.exists(filepath):
        create_channel_config(filepath)
    with open(filepath, "r") as f:
        config_dict = json.loads(f.readline())
    return config_dict
    
        
async def react_to_msg(ctx, react):
    def is_emoji(string):
        if len(string) == 1:
            # Range of Unicode codepoints for emojis
            if 0x1F300 <= ord(string) <= 0x1F6FF:
                return True
        return False
    
    if react:
        if not random.randint(0,10) and ctx.author.id != 1097302679836971038:
            system_msg = "Send only an emoji as a discord reaction to the following chat message"
            message = ctx.content[0]
            headers = { 
                'Content-Type': 'application/json', 
                'Authorization': f'Bearer {os.getenv("openai.api_key")}',
            }
            
            data = { 
                "model": "gpt-3.5-turbo", 
                "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": message}]
            }

            url = "https://api.openai.com/v1/chat/completions"
            
            try:
                async with bot.http_session.post(url, headers=headers, json=data) as resp:
                    response_data = await resp.json()
                    reaction = response_data['choices'][0]['message']['content'].strip()
                if is_emoji(reaction):
                    await ctx.add_reaction(reaction)
                else:
                    await ctx.add_reaction("😓")
            except Exception as error:
                print("Some error happened while trying to react to a message")
                await handle_error(error)
            
async def log_chat_and_get_history(ctx, logfile, channel_vars):
    log_line = ''           
    log_line += ctx.content
    log_line =  ctx.author.name + ": " + log_line  +"\n"
    chat_history = ""
    print("Logging: " + log_line, end="")
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(log_line)
    with open(logfile, "r", encoding="utf-8") as f:
        for line in (f.readlines() [-int(channel_vars["chat_history_len"]):]):
            chat_history += line
    return chat_history

        
async def chat_response(ctx, channel_vars, chat_history_string): 
    async with ctx.channel.typing(): 
        await asyncio.sleep(1)
        prompt = f"You are a {channel_vars['personality']} chat bot named Sparkytron 3000 created by @phixxy.com. Your personality should be {channel_vars['personality']}. You are currently in a {channel_vars['channel_topic']} chatroom. The message history is: {chat_history_string}"
        headers = { 
            'Content-Type': 'application/json', 
            'Authorization': f'Bearer {os.getenv("openai.api_key")}',
        }
        
        data = { 
            "model": "gpt-3.5-turbo", 
            "messages": [{"role": "user", "content": prompt}]
        }

        url = "https://api.openai.com/v1/chat/completions"

        try: 
            async with bot.http_session.post(url, headers=headers, json=data) as resp:
                response_data = await resp.json() 
                response = response_data['choices'][0]['message']['content']
                if "Sparkytron 3000:" in response[0:17]:
                    response = response.replace("Sparkytron 3000:", "")
                max_len = 1999
                if len(response) > max_len:
                    messages=[response[y-max_len:y] for y in range(max_len, len(response)+max_len,max_len)]
                else:
                    messages=[response]
                for message in messages:
                    await ctx.channel.send(message)

        except Exception as error: 
            await handle_error(error)
    
async def folder_setup():
    # Only tmp, extensions and data are supported, all other folders only exist for backwards compatibility and will be removed soon!
    folder_names = ["tmp", "extensions", "data", "plugins", "tmp/sfw", "tmp/nsfw", "tmp/meme", "channels", "users", "channels/config", "channels/logs", "databases", "databases/currency", "databases/currency/players"]
    for folder_name in folder_names:
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)
    return folder_names
            
async def delete_all_files(path, safe_folders):
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
            await handle_error(error)
            
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
        if plugin_file != '__init__.py' and plugin_file[-3:] == '.py':
            await bot.load_extension(f'extensions.{plugin_file[:-3]}')
    print('We have logged in as {0.user}'.format(bot))
    task_loop.start()
        
@bot.event
async def on_reaction_add(reaction, user):
    if not random.randint(0,9):
        message = reaction.message
        emoji = reaction.emoji
        await message.add_reaction(emoji)
    

async def pkmn_msg(discord_id):
    path = "databases/pokemon/"+str(discord_id)+'.json'
    if os.path.isfile(path):
        with open(path, 'r') as f:
            json_data = json.loads(f.readline())
            json_data['buddy_xp'] += random.randint(1,5)
            json_data = json.dumps(json_data)
        with open(path, 'w') as f:
            f.writelines(json_data)


@bot.event
async def on_message(ctx):
    #log stuff
    logfile = "channels/logs/{0}.log".format(str(ctx.channel.id))
    channel_vars = await get_channel_config(ctx.channel.id)
    chat_history_string = await log_chat_and_get_history(ctx, logfile, channel_vars)

    #add pokemon xp
    await pkmn_msg(ctx.author.id)
    
    #handle non-text channels (dms, etc)
    if ctx.channel.type.value != 0 and ctx.author.id != 242018983241318410:
        #This used to notify the user it cannot respond in this channel, but that spammed threads
        return
    
    await react_to_msg(ctx, channel_vars["react_to_msgs"]) #emoji reactions
    
    if channel_vars["commands_enabled"] or (ctx.author.id == 242018983241318410 and ctx.content[0] == "!"):
        await bot.process_commands(ctx)
        if not channel_vars["commands_enabled"]:
            await ctx.channel.send("This command only ran because you set it to allow to run even when commands are disabled")

    if channel_vars["chat_enabled"] and not ctx.author.bot:
        if ctx.content and ctx.content[0] != "!":
            await chat_response(ctx, channel_vars, chat_history_string)
        elif not ctx.content:
            await chat_response(ctx, channel_vars, chat_history_string)


bot.run(discord_token)
