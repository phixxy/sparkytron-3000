import discord
from discord.ext import commands, tasks
from discord.utils import get
import shutil
import json
import random
import time
import os
import asyncio
import subprocess
from dotenv import load_dotenv

import aiohttp
import asyncssh

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

async def upload_sftp(local_filename, server_folder, server_filename):
    remotepath = server_folder + server_filename
    async with asyncssh.connect(ftp_server, username=ftp_username, password=ftp_password) as conn:
        async with conn.start_sftp_client() as sftp:
            await sftp.put(local_filename, remotepath=remotepath)
    
async def handle_error(error):
    print(error)
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log_line = current_time + ': ' + str(error) + '\n'
    with open("databases/error_log.txt", 'a') as f:
        f.write(log_line)
    return error

async def upload_ftp_ai_images(folder):
    for filename in os.listdir(folder):
        if filename[-4:] == '.png':
            filepath = folder + filename
            prompt = "Unknown Prompt" # Will have to update this later

            html_file = "phixxy.com/ai-images/index.html"
            html_insert = '''<!--REPLACE THIS COMMENT-->
                <div>
                    <img src="<!--filename-->" loading="lazy">
                    <p class="image-description"><!--description--></p>
                </div>'''
            server_folder = (os.getenv('ftp_public_html') + 'ai-images/')
            new_filename = str(time.time_ns()) + ".png"
            await upload_sftp(filepath, server_folder, new_filename)
            print("Uploaded", new_filename)
            with open(html_file, 'r') as f:
                html_data = f.read()
            html_insert = html_insert.replace("<!--filename-->", new_filename)
            html_insert = html_insert.replace("<!--description-->", prompt)
            html_data = html_data.replace("<!--REPLACE THIS COMMENT-->", html_insert)
            with open(html_file, "w") as f:
                f.writelines(html_data)
            await upload_sftp(html_file, server_folder, "index.html")
            os.rename(filepath, f"tmp/{new_filename}")

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
    folder_names = ["tmp", "tmp/sfw", "tmp/nsfw", "tmp/meme", "channels", "users", "channels/config", "channels/logs", "databases", "databases/currency", "databases/currency/players"]
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

async def delete_derp_files(server_folder):
    async with asyncssh.connect(ftp_server, username=ftp_username, password=ftp_password) as conn:
        async with conn.start_sftp_client() as sftp:
            for filename in (await sftp.listdir(server_folder)):
                if filename == '.' or filename == '..' or filename == 'style.css' or filename == 'myScript.js':
                    pass
                else:
                    try:
                        print("Deleting", filename)
                        await sftp.remove(server_folder+filename)
                    except:
                        print("Couldn't delete", filename)

async def meme_handler(folder):
    for file in os.listdir(folder):
        filepath = folder + file
        await update_meme_webpage(filepath)

            
@tasks.loop(seconds=1)  # Run the task every second
async def task_loop():
    current_time = time.localtime()
    #Run every minute
    if current_time.tm_sec == 0:
        await meme_handler('tmp/meme/')
        await upload_ftp_ai_images('tmp/sfw/')

    #Run daily tasks
    if current_time.tm_hour == 17 and current_time.tm_min == 0 and current_time.tm_sec == 0:
        bot_stuff = bot.get_channel(544408659174883328)
        output = 'The following tasks failed:\n```'
        failed_tasks = []
        await bot_stuff.send("<@242018983241318410> The current time is 5pm. Running daily tasks!")
        try:
            await delete_all_files("tmp/")
        except Exception as error:
            await handle_error(error)
            failed_tasks.append("Delete tmp/")
        try:
            await delete_derp_files("/home/debian/websites/derp.phixxy.com/files/")
        except Exception as error:
            await handle_error(error)
            failed_tasks.append("Delete derp files")
        if failed_tasks != []:
            for failed_task in failed_tasks:
                output += failed_task + '\n'
            output += '```'
            await bot_stuff.send(output)
        else:
            await bot_stuff.send("All daily tasks successfully ran!")
            
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
    # Import plugins from plugins folder
    for plugin_file in os.listdir('plugins/'):
        if plugin_file != '__init__.py' and plugin_file[-3:] == '.py':
            await bot.load_extension(f'plugins.{plugin_file[:-3]}')

    print('We have logged in as {0.user}'.format(bot))
    #stuff to do if first run
    folders_made = await folder_setup()
    await delete_all_files("tmp/", folders_made)
    task_loop.start()
    

async def update_meme_webpage(filename):
        server_folder = (os.getenv('ftp_public_html') + 'ai-memes/')
        new_file_name = str(time.time_ns()) + ".png"
        await upload_sftp(filename, server_folder, new_file_name)
        print("Uploaded", new_file_name)
        with open("phixxy.com/ai-memes/index.html", 'r') as f:
            html_data = f.read()
        html_insert = '<!--ADD IMG HERE-->\n        <img src="' + new_file_name + '" loading="lazy">'
        html_data = html_data.replace('<!--ADD IMG HERE-->',html_insert)
        with open("phixxy.com/ai-memes/index.html", "w") as f:
            f.writelines(html_data)
        await upload_sftp("phixxy.com/ai-memes/index.html", server_folder, "index.html")
        os.rename(filename, 'tmp/' + new_file_name)


@bot.command(
    description="Poll", 
    help='Create a poll with up to 9 options. Usage: !poll "Put question here" "option 1" "option 2"', 
    brief="Enable or disable bot reactions"
    ) 
async def poll(ctx, question, *options: str):
    if len(options) > 9:
        await ctx.send("Error: You cannot have more than 9 options")
        return

    embed = discord.Embed(title=question, colour=discord.Colour(0x283593))
    for i, option in enumerate(options):
        embed.add_field(name=f"Option {i+1}", value=option, inline=False)

    message = await ctx.send(embed=embed)
    numbers = {0: "\u0030\ufe0f\u20e3", 1: "\u0031\ufe0f\u20e3", 2: "\u0032\ufe0f\u20e3", 3: "\u0033\ufe0f\u20e3", 4: "\u0034\ufe0f\u20e3", 5: "\u0035\ufe0f\u20e3", 6: "\u0036\ufe0f\u20e3", 7: "\u0037\ufe0f\u20e3", 8: "\u0038\ufe0f\u20e3", 9: "\u0039\ufe0f\u20e3"}
    for i in range(len(options)):
        await message.add_reaction(numbers.get(i+1))
        
@bot.command(
    description="Roll", 
    help="Rolls dice mostly for Dungeons and Dragons type games. Usage: !roll 3d6+2", 
    brief="Simulate rolling dice"
    ) 
async def roll(ctx, dice_string):
    dice_parts = dice_string.split('d')
    num_dice = int(dice_parts[0])
    if '+' in dice_parts[1]:
        die_parts = dice_parts[1].split('+')
        die_size = int(die_parts[0])
        modifier = int(die_parts[1])
    elif '-' in dice_parts[1]:
        die_parts = dice_parts[1].split('-')
        die_size = int(die_parts[0])
        modifier = -int(die_parts[1])
    else:
        die_size = int(dice_parts[1])
        modifier = 0

    rolls = [random.randint(1, die_size) for i in range(num_dice)]
    dice_str = ' + '.join([str(roll) for roll in rolls])
    total = sum(rolls) + modifier

    await ctx.send(f'{dice_str} + {modifier} = {total}' if modifier != 0 else f'{dice_str} = {total}')

        
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
