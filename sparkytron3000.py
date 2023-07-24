import discord
from discord.ext import commands, tasks
from discord.utils import get
import shutil
import json
import requests
import random
import time
import os
import io
import base64
import asyncio
import sys
import subprocess
import math
from PIL import Image, PngImagePlugin
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import aiohttp
import aioftp

#Stable Diffusion
#Set this env variable to http://host:port or "disabled"
#os.getenv('stablediffusion_url')

#env vars START
load_dotenv()

imgflip_username = os.getenv('imgflip_username')
imgflip_password = os.getenv('imgflip_password')
discord_token    = os.getenv('discord_token')
eleven_labs_api_key = os.getenv('eleven_labs_api_key')
ftp_server = os.getenv('ftp_server')
ftp_username = os.getenv('ftp_username')
ftp_password = os.getenv('ftp_password')
ftp_ai_images = os.getenv('ftp_ai_images')
ftp_ai_memes = os.getenv('ftp_ai_memes')
ftp_ai_webpage = os.getenv('ftp_ai_webpage')
ftp_public_html = os.getenv('ftp_public_html')

#env vars END

#discord stuff START
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
#discord stuff END

@bot.command(
    description="Moderate", 
    help="This currently tool works by replacing the filename on the ftp server with a black image. The description will remain the same and may need to be altered.", 
    brief="Moderation Tools"
    )
async def moderate(ctx, filename):
    await upload_ftp("blank_image.png", os.getenv('ftp_ai_images'), filename)
    output = "Image " + filename + " replaced"
    await ctx.send(output)
    
async def upload_ftp(local_filename, server_folder, server_filename):
    client = aioftp.Client()
    await client.connect(ftp_server)
    await client.login(ftp_username, ftp_password)
    await client.change_directory(server_folder)
    await client.upload(local_filename, server_folder+server_filename, write_into=True)
    await client.quit()
    
async def handle_error(error):
    print(error)
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log_line = current_time + ': ' + str(error) + '\n'
    with open("databases/error_log.txt", 'a') as f:
        f.write(log_line)
    return error
    

async def upload_ftp_ai_images(filename, prompt):
    html_file = "phixxy.com/ai-images/index.html"
    html_insert = '''<!--REPLACE THIS COMMENT-->
        <div>
            <img src="<!--filename-->" loading="lazy">
            <p class="image-description"><!--description--></p>
        </div>'''
    img_list = []
    server_folder = os.getenv('ftp_ai_images')
    client = aioftp.Client()
    await client.connect(ftp_server)
    await client.login(ftp_username, ftp_password)
    await client.change_directory(server_folder)
    server_files = await client.list()
    try:
        file_count = int(len(server_files))
    except:
        file_count = 0
    new_file_name = str(file_count) + ".png"
    await client.upload(filename, new_file_name, write_into=True)
    print("Uploaded", new_file_name)
    with open(html_file, 'r') as f:
        html_data = f.read()
    html_insert = html_insert.replace("<!--filename-->", new_file_name)
    html_insert = html_insert.replace("<!--description-->", prompt)
    html_data = html_data.replace("<!--REPLACE THIS COMMENT-->", html_insert)
    with open(html_file, "w") as f:
        f.writelines(html_data)
    await client.upload(html_file, "index.html", write_into=True)
    await client.quit()

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
    
async def answer_question(topic, model="gpt-3.5-turbo"):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.getenv("openai.api_key")}',
    }

    data = {
        "model": model,
        "messages": [{"role": "user", "content": topic}]
    }

    url = "https://api.openai.com/v1/chat/completions"

    try:
        async with bot.http_session.post(url, headers=headers, json=data) as resp:
            response_data = await resp.json()
            response = response_data['choices'][0]['message']['content']
            return response

    except Exception as error:
        return await handle_error(error)
    
def extract_key_value_pairs(input_str):
    output_str = input_str
    
    key_value_pairs = {}
    tokens = input_str.split(', ')
    for token in tokens:
        if '=' in token:
            key, value = token.split('=')
            key_value_pairs[key] = value
            output_str = output_str.replace(token+', ', '') # Remove the key-value pair from the output string
    
    return key_value_pairs, output_str
    
def combine_dicts(dict1, dict2): #prioritizes dict2 args
    combined_dict = {}
    for key in dict1:
        combined_dict[key] = dict1[key]
    for key in dict2:
        combined_dict[key] = dict2[key]
    return combined_dict
    
def my_open_img_file(path):
    img = Image.open(path)
    w, h = img.size
    encoded = ""  
    with io.BytesIO() as output:
        img.save(output, format="PNG")
        contents = output.getvalue()
        encoded = str(base64.b64encode(contents), encoding='utf-8')
    img.close()
    return encoded

async def look_at(ctx, look=False):
    metadata = ""
    if look:
        url = os.getenv('stablediffusion_url')
        if url == "disabled":
            return
        for attachment in ctx.attachments:
            if attachment.url.endswith(('.jpg', '.png')):
                print("image seen")
                
                async with bot.http_session.get(attachment.url) as response:
                    imageName = "tmp/" + str(len(os.listdir('tmp/'))) + '.png'
                    
                    with open(imageName, 'wb') as out_file:
                        print('Saving image: ' + imageName)
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            out_file.write(chunk)

                    img_link = my_open_img_file(imageName)
                    
                    try:
                        payload = {"image": img_link}
                        async with bot.http_session.post(f'{url}/sdapi/v1/interrogate', json=payload) as response:
                            data = await response.json()
                            description = data.get("caption")
                            description = description.split(',')[0]
                            metadata += f"<image:{description}>\n"
                    except aiohttp.ClientError as error:
                        await handle_error(error)
                        return "ERROR: CLIP may not be running. Could not look at image."
    
    return metadata


    
def edit_channel_config(channel_id, key, value):
    config_file = "channels/config/" + str(channel_id) + ".json"
    #if not os.path.exists(config_file):
    #    create_channel_config(config_file)
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    config_data[key] = value
    with open(config_file, "w") as f:
        json.dump(config_data, f)
        
async def react_to_msg(ctx, react):
    if True: #this should say if react: but I am leaving it because people are enjoying it for now
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
                    reaction = response_data['choices'][0]['message']['content']
                await ctx.add_reaction(reaction.strip())
            except Exception as error:
                print("Some error happened while trying to react to a message")
                await handle_error(error)
            
async def log_chat_and_get_history(ctx, logfile, channel_vars):
    metadata = await look_at(ctx, channel_vars["look_at_images"])
    log_line = metadata            
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
    folder_names = ["tmp", "channels", "users", "channels/config", "channels/logs", "databases", "databases/currency", "databases/currency/players"]
    for folder_name in folder_names:
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)
            
async def delete_all_files(path):
    for filename in os.listdir(path):
        if os.path.isdir(path+filename):
            shutil.rmtree(path+filename)
        elif os.path.isfile(path+filename):
            os.remove(path+filename)


            
@tasks.loop(seconds=1)  # Run the task every second
async def task_loop():
    current_time = time.localtime()
    
    #Run daily tasks
    if current_time.tm_hour == 17 and current_time.tm_min == 0 and current_time.tm_sec == 0:
        bot_stuff = bot.get_channel(544408659174883328)
        output = 'The following tasks failed:\n```'
        failed_tasks = []
        await bot_stuff.send("<@242018983241318410> The current time is 5pm. Running daily tasks!")
        try:
            await generate_blog(bot_stuff)
        except Exception as error:
            await handle_error(error)
            failed_tasks.append("Blogpost")
        try:
            await delete_all_files("tmp/")
        except Exception as error:
            await handle_error(error)
            failed_tasks.append("Delete tmp/")
        if failed_tasks != []:
            for failed_task in failed_tasks:
                output += failed_task + '\n'
            output += '```'
            await bot_stuff.send(output)
        else:
            await bot_stuff.send("All daily tasks successfully ran!")
            
async def create_session():
    #timeout = aiohttp.ClientTimeout(total=30)
    return aiohttp.ClientSession()#timeout=timeout)

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
    print('We have logged in as {0.user}'.format(bot))
    #stuff to do if first run
    await folder_setup()
    await delete_all_files("tmp/")
    task_loop.start()
    
@bot.command(
    description="Update", 
    help="This will update sparkytron to the most recent version on github. Only privileged users can run this command! Usage: !update", 
    brief="Runs git pull",
    hidden=True
    )           
async def update(ctx):
    if ctx.author.id == 242018983241318410:
        output = subprocess.run(["git","pull"],capture_output=True)
        if output.stderr:
            await ctx.send("Update Failed")
            await ctx.send(output.stderr.decode('utf-8'))
        else:
            await ctx.send(output.stdout.decode('utf-8'))
    else:
        await ctx.send("You don't have permission to do this.")
        
@bot.command(
    description="Currency", 
    help="Server currency. You can run !currency claim to get started!", #This needs an overhaul
    brief="Server currency tools"
    )        
async def currency(ctx, arg1=None, arg2=None, arg3=None, arg4=None):
    
    def read_db(filepath):
        with open(filepath,"r") as fileobj:
            db_content = json.load(fileobj)
        #print(db_content,type(db_content))
        return db_content

    def save_to_db(filepath,db_content):
        with open(filepath,"w") as fileobj:
            json.dump(db_content,fileobj,indent=4)

    def add_currency(filepath,amount):
        player_db = read_db(filepath)
        player_db["currency"] += amount
        save_to_db(filepath,player_db)
        return player_db
        
    def calc_level_from_xp(xp):
        level = min(100,math.floor(0.262615*xp**0.3220627))
        return level
    
    def add_xp(filepath,player_db,time_spent):
        activity = player_db["status"]["current_activity"]
        starting_xp = player_db["skills"][activity]["xp"]
        starting_level = player_db["skills"][activity]["level"]
        

        if activity == "mining":
            equipment_level = player_db["equipment"]["pickaxe"]["level"]
            xp_gained = (time_spent) * equipment_level # SKILL LEVEL of XP / SEC
        player_db["skills"][activity]["xp"] += xp_gained
        new_xp = starting_xp + xp_gained
        new_level = calc_level_from_xp(new_xp) #calculate with curve here
        player_db["skills"][activity]["level"] = new_level
        levels_gained = new_level - starting_level

        summary = "" #summary should include xp gained, levels gained (only if any were gained), current level (or new level)
        summary += "You gained {} {} xp!".format(xp_gained, activity)
        if levels_gained > 0: #if levels gained > 0, then include levels gained in summary
            summary += "\nYou gained {} {} level(s)! You are now level {}.".format(levels_gained, activity, new_level)

        save_to_db(filepath, player_db)
        return player_db,summary

    def add_resources(filepath,player_db,time_spent):

        mining_resources = {
            "sapphire": {
                "value": 100,
                "amount": 0
            },
            "emerald": {
                "value": 250,
                "amount": 0
            },
            "ruby": {
                "value": 1000,
                "amount": 0
            },
            "diamond": {
                "value": 3000,
                "amount": 0
            }
        }

        if player_db["status"]["current_activity"] == "mining":
            pick_power = player_db["equipment"]["pickaxe"]["power"]
            pick_level = player_db["equipment"]["pickaxe"]["level"]
            mining_level = player_db["skills"]["mining"]["level"]
            numerator = pick_power + pick_level + mining_level
            denominator = 1000
            items_gained = []
            time_summary = time.strftime("%H:%M:%S", time.gmtime(time_spent))

            for second in range(0,time_spent):
                roll = random.randint(0,denominator)
                if roll <= numerator: #get a resource
                    roll2 = random.randint(0,100)
                    if roll2 <= 50:
                        mining_resources["sapphire"]["amount"] += 1
                    elif roll2 <=80:
                        mining_resources["emerald"]["amount"] += 1
                    elif roll2 <= 95:
                        mining_resources["ruby"]["amount"] += 1
                    else:
                        mining_resources["diamond"]["amount"] += 1
            for item in mining_resources:
                mined_amount = mining_resources[item]["amount"]
                if item in player_db["items"]:
                    player_db["items"][item]["amount"] += mined_amount
                    items_gained.append(item.title())
                    items_gained.append(mined_amount)
                else:
                    player_db["items"][item] = mining_resources[item]
                    items_gained.append(item.title())
                    items_gained.append(mined_amount)

            save_to_db(filepath, player_db)

            summary = "You spent {} mining. You mined {} x{}, {} x{}, {} x{}, and {} x{}.".format(time_summary, *items_gained)

            return player_db,summary
            
    async def transfer_currency(filepath, player_db, player_id, amount):
        try:
            amount = int(amount)
            player2_filepath = "currency/players/" + str(player_id) + ".json"
            player2_db = read_db(player2_filepath)
            if player_db["currency"] >= amount:
                add_currency(filepath, -amount)
                add_currency(player2_filepath,amount)
                await ctx.send("Sent " + str(amount) + " sparks to " + str(player_id))
        except FileNotFoundError:
            await ctx.send("They don't seem to be playing the game.")
        
    
    async def show_levels(player_db):
        output = ''
        for skill in player_db["skills"]:
            output += skill + ': ' + str(player_db["skills"][skill]["level"]) + '\n'
        await ctx.send(output)
        
    async def show_currency(player_db):
        output = 'Sparks: ' + str(player_db["currency"])
        await ctx.send(output)
        
    async def show_items(player_db):
        output = ''
        for item in player_db["items"]:
            output += item + ': ' + str(player_db["items"][item]["amount"]) + '\n'
        await ctx.send(output)
            

    async def stop_activity(filepath,player_db):
        if player_db["status"]["current_activity"] == "idle":
            await ctx.send("You are currently idle. There is no activity to stop.")
        else:
            time_spent = int(time.time() - player_db["status"]["start_time"]) #integer in seconds
            player_db, xp_summary = add_xp(filepath,player_db,time_spent)
            player_db, resources_summary = add_resources(filepath,player_db,time_spent)
            await ctx.send(xp_summary)
            await ctx.send(resources_summary)
            player_db["status"]["current_activity"] = "idle"
            save_to_db(filepath,player_db)
        
    async def claim(filepath, player_db):
        if time.time() - player_db["status"]["last_claimed"] >= 86400:
            player_db = add_currency(filepath, 100)
            player_db["status"]["last_claimed"] = time.time()
            save_to_db(filepath,player_db)
            await ctx.send("You claimed 100 sparks!")
        else:
            await ctx.send("Sorry, you already claimed your sparks today.")
        
    async def mine(filepath, player_db):
        if player_db["status"]["current_activity"] == "idle":
            player_db["status"]["current_activity"] = "mining"
            player_db["status"]["start_time"] = time.time()
            save_to_db(filepath, player_db)
            await ctx.send("You start mining.")
        elif player_db["status"]["current_activity"] == "mining":
            await ctx.send("You are already mining!")
        else:
            await ctx.send("You must stop " + player_db["status"]["current_activity"] + " before you start mining!")
            
    async def gamble(filepath, player_db):
        pass
    
    working_dir = "databases/currency/"
    players_dir = "players/"
    sender_id = str(ctx.author.id)
    default_db = read_db("{0}{1}default.json".format(working_dir, players_dir))
    filepath = '{0}{1}{2}.json'.format(working_dir, players_dir, sender_id)

    try:
        player_db = read_db(filepath)
    except FileNotFoundError:
        save_to_db(filepath,default_db)
        player_db = read_db(filepath)
        
    if arg1 == "claim":
        await claim(filepath, player_db)
        player_db = read_db(filepath)
    elif arg1 == "stop":
        await stop_activity(filepath, player_db)
        player_db = read_db(filepath)
    elif arg1 == "mine":
        await mine(filepath, player_db)
        player_db = read_db(filepath)
    elif arg1 == "levels":
        await show_levels(player_db)
    elif arg1 == "items":
        await show_items(player_db)
    elif (arg1 == "send" or arg1 == "give") and arg2 and arg3:
        await transfer_currency(filepath, player_db, arg2, arg3) 
        player_db = read_db(filepath)
    else:
        await show_currency(player_db)

                
                
@bot.command(
    description="Meme", 
    help="Generates a meme based on input. Usage: !meme (topic)", 
    brief="Generate a meme"
    )       
async def meme(ctx):
    async def update_meme_webpage(filename):
        server_folder = os.getenv('ftp_ai_memes')
        client = aioftp.Client()
        await client.connect(ftp_server)
        await client.login(ftp_username, ftp_password)
        await client.change_directory(server_folder)
        server_files = await client.list()
        try:
            file_count = len(server_files)
        except:
            file_count = 0
        new_file_name = str(file_count) + ".png"
        await client.upload(filename, new_file_name, write_into=True)
        print("Uploaded", new_file_name)
        with open("phixxy.com/ai-memes/index.html", 'r') as f:
            html_data = f.read()
        html_insert = '<!--ADD IMG HERE-->\n        <img src="' + new_file_name + '" loading="lazy">'
        html_data = html_data.replace('<!--ADD IMG HERE-->',html_insert)
        with open("phixxy.com/ai-memes/index.html", "w") as f:
            f.writelines(html_data)
        await client.upload("phixxy.com/ai-memes/index.html", "index.html", write_into=True)
        await client.quit()
    
    
    async def generate_random_meme(topic):
        async with bot.http_session.get('https://api.imgflip.com/get_memes') as resp:
            response_data = await resp.json()
            response = response_data['data']['memes']
        memepics = [{'name':image['name'],'url':image['url'],'id':image['id']} for image in response]
        
        #Pick a meme format
        memenumber = random.randint(1,99)
        meme_name = response[memenumber-1]['name']
        panel_count = response[memenumber-1]['box_count']
        print("panel_count ",panel_count)
        panel_text = await answer_question("Create text for a meme. The meme is " + meme_name + ". It has " + str(panel_count) + " panels. Only create one meme. Do not use emojis or hashtags! Use the topic: " + topic + ". Use the output format (DO NOT USE EXTRA NEWLINES AND DO NOT DESCRIBE THE PICTURE IN YOUR OUTPUT): \n1: [panel 1 text]\n2: [panel 2 text]")
        
        id = memenumber
        
        params = {
            'username':"Bottlec4p",
            'password':'Cookies@22',
            'template_id':memepics[id-1]['id']
        }
        boxes = []
        text = panel_text.split('\n')
        for x in range(len(text)):
            if text[x].strip() != "":
                item = text[x][3:]
                if len(params)-3 < panel_count:
                    dictionary = {"text":item, "color": "#ffffff", "outline_color": "#000000"}
                    boxes.append(dictionary)

        for i, box in enumerate(boxes):
            params[f"boxes[{i}][text]"] = box["text"]
            params[f"boxes[{i}][color]"] = box["color"]
            params[f"boxes[{i}][outline_color]"] = box["outline_color"]
            
        URL = 'https://api.imgflip.com/caption_image'

        try:
            async with bot.http_session.post(URL, params=params) as resp:
                response = await resp.json()
            print(f"Generated Meme = {response['success']}\nImage Link = {response['data']['url']}\nPage Link = {response['data']['page_url']}")
            image_link = response['data']['url']
        except Exception as error:
            await handle_error(error)
        try:
    #------------------------------------Saving Image Using Requests---------------------------------#
            filename = memepics[id-1]['name']
            response = requests.get(f"{response['data']['url']}")
            folder = "tmp/"
            filename = folder + topic + str(len(os.listdir(folder))) + ".jpg"
            file = open(filename, "wb")
            file.write(response.content)
            file.close()
            print("Meme was Saved Successfuly")
        except Exception as error:
            await handle_error(error)
            print("Something's Wrong with the urllib So try again")
        return image_link, filename
    
    try:
        topic = ctx.message.content.split(" ", maxsplit=1)[1]
        link, filepath = await generate_random_meme(topic)
        channel_vars = await get_channel_config(ctx.channel.id)
        try:
            if channel_vars["ftp_enabled"]:
                await update_meme_webpage(filepath)
        except Exception as error:
            print("COULDN'T UPLOAD TO FTP!")
            await handle_error(error)
        await ctx.send(link)
    except Exception as error:
        await handle_error(error)
        await ctx.send('Something went wrong try again. Usage: !meme (topic)')
        
@bot.command(
    description="RSGP", 
    help="Uses probably outdated information to calculate how much rsgp is worth in usd. Usage: !rsgp (amount)", 
    brief="Runescape gold to usd"
    )       
async def rsgp(ctx, amount):
    output = ""
    cost_per_bil = 25.50 #1b rsgp to usd
    cost_per_bil_os = 210
    gold_per_bond = 70000000
    gold_per_bond_os = 7000000
    cost_per_bond = 8 #dollars usd
    bondcost = (int(amount)/gold_per_bond) * cost_per_bond
    rwtcost = (int(amount) * cost_per_bil / 1000000000)
    dollar_gp = (int(amount)*1000000000)/cost_per_bil
    osbondcost = (int(amount)/gold_per_bond_os) * cost_per_bond
    osrwtcost = (int(amount) * cost_per_bil_os / 1000000000)
    osdollar_gp = (int(amount)*1000000000)/cost_per_bil_os
    output += str(amount) + ' rs3 gp would cost: $' + str(round(rwtcost,2)) + " (RWT)\n"
    output += str(amount) + ' rs3 gp would cost: $' + str(round(bondcost,2)) + " (Bonds)\n"
    output += str(amount) + ' dollars spent on rs3 gp would be: ' + str(round(dollar_gp,2)) + " (RS3 GP)\n"
    output += str(amount) + ' osrs gp would cost: $' + str(round(rwtcost,2)) + " (RWT)\n"
    output += str(amount) + ' osrs gp would cost: $' + str(round(bondcost,2)) + " (Bonds)\n"
    output += str(amount) + ' dollars spent on osrs gp would be: ' + str(round(dollar_gp,2)) + " (OSRS GP)\n"
    await ctx.send(output)
    
@bot.command(
    description="Blog", 
    help="Adds your topic to the list of possible future blog topics. Usage: !suggest_blog (topic)", 
    brief="Suggest a blog topic"
    )
async def blog(ctx, *args):
    message = ' '.join(args)
    if '\n' in message:
        await ctx.send("Send only one topic at a time.")
        return
    else:
        blogpost_file = "databases/blog_topics.txt"
        with open(blogpost_file, 'a') as f:
            f.writelines(message+'\n')
        await ctx.send("Saved suggestion!")

@bot.command()
async def generate_blog(ctx):
    start_time = time.time()
    topic = ''
    filename = "phixxy.com/ai-blog/index.html"
    with open(filename, 'r', encoding="utf-8") as f:
        html_data = f.read()
    current_time = time.time()
    current_struct_time = time.localtime(current_time)
    date = time.strftime("%B %d, %Y", current_struct_time)
    if date in html_data:
        await ctx.send("I already wrote a blog post today!")
        return
    blogpost_file = "databases/blog_topics.txt"
    blog_subscribers = ["276197608735637505","242018983241318410"]
    if os.path.isfile(blogpost_file):
        with open(blogpost_file, 'r') as f:
            blogpost_topics = f.read()
            f.seek(0)
            topic = f.readline()
            blogpost_topics = blogpost_topics.replace(topic, '')
        with open(blogpost_file, 'w') as f:
            f.write(blogpost_topics)
    if topic != '':
        await ctx.send("Writing blogpost")
    else:
        await ctx.send("No topic given for blogpost, generating one.")
        topic = await answer_question("Give me one topic for an absurd blogpost.")
        
    
    post_div = '''<!--replace this with a post-->
            <div class="post">
                <h2 class="post-title"><!--POST_TITLE--></h2>
                <p class="post-date"><!--POST_DATE--></p>
                <div class="post-content">
                    <!--POST_CONTENT-->
                </div>
            </div>'''
    title_prompt = 'generate an absurd essay title about ' + topic
    title = await answer_question(title_prompt, model="gpt-3.5-turbo")
    prompt = 'Write a satirical essay with a serious tone titled: "' + title + '". Do not label parts of the essay.'
    content = await answer_question(prompt, model="gpt-4")
    if title in content[:len(title)]:
        content = content.replace(title, '', 1)
    content = f"<p>{content}</p>"
    content = content.replace('\n\n', "</p><p>")
    content = content.replace("<p></p>", '')

    post_div = post_div.replace("<!--POST_TITLE-->", title)
    post_div = post_div.replace("<!--POST_DATE-->", date)
    post_div = post_div.replace("<!--POST_CONTENT-->", content)
    
    html_data = html_data.replace("<!--replace this with a post-->", post_div)
    with open(filename, 'w', encoding="utf-8") as f:
        f.write(html_data)
    
    
    await upload_ftp(filename, "/media/sdq1/bottlecap/www/phixxy.com/public_html/ai-blog/", "index.html")
    run_time = time.time() - start_time
    print("It took " + str(run_time) + " seconds to generate the blog post!")
    output = "Blog Updated! (" + str(run_time) + " seconds) https://phixxy.com/ai-blog"
    output += '\nNotifying subscribers: '
    for subscriber in blog_subscribers:
        output += '<@' + subscriber + '> '
    await ctx.send(output)
        

@bot.command(
    description="Question", 
    help="Ask a raw chatgpt question. Usage: !question (question)", 
    brief="Get an answer"
    )        
async def question(ctx):
    question = ctx.message.content.split(" ", maxsplit=1)[1]
    answer = await answer_question(question)
    chunks = [answer[i:i+1999] for i in range(0, len(answer), 1999)]
    for chunk in chunks:
        await ctx.send(chunk)
        
@bot.command(
    description="Question GPT4", 
    help="Ask GPT4 a question. Usage: !question_gpt4 (question)", 
    brief="Get an answer"
    )         
async def question_gpt4(ctx):
    question = ctx.message.content.split(" ", maxsplit=1)[1]
    answer = await answer_question(question, "gpt-4")
    chunks = [answer[i:i+1999] for i in range(0, len(answer), 1999)]
    for chunk in chunks:
        await ctx.send(chunk)

@bot.command(
    description="Highscores", 
    help="Shows a bar graph of users in this channel and how many messages they have sent.", 
    brief="Display chat highscores"
    ) 
async def highscores(ctx, limit=0):
    filename = str(ctx.channel.id) + ".log"
    with open("channels/logs/" + filename, 'r', encoding="utf-8") as logfile:
        data = logfile.readlines()
        logfile.close()
    
    def is_username(user):
        for character in user:
            if character.isupper():
                return False
            if not (character.isalpha() or character.isdigit() or character == '.' or character == '_'):
                return False
        return True
        

    user_message_counts = {}    
    for line in data:
        try:
            user = line[0:line.find(':')]
            if is_username(user):
                if user not in user_message_counts and user != "" and len(user) <= 32:
                    user_message_counts[user] = 1
                else:
                    user_message_counts[user] += 1
        except Exception as error:
            await handle_error(error)
    
    def remove_dict_keys_if_less_than_x(dictionary,x):
        for key in dictionary:
            if dictionary[key] <= x:
                dictionary.pop(key)
                return remove_dict_keys_if_less_than_x(dictionary,x)
        return dictionary
            


    print(user_message_counts)   
    remove_dict_keys_if_less_than_x(user_message_counts,limit) 
    keys = list(user_message_counts.keys())
    values = list(user_message_counts.values())
    
    fig, ax = plt.subplots()
    bar_container = ax.barh(keys, values)
    ax.set_xlabel("Message Count")
    ax.set_ylabel("Username")
    ax.set_title("Messages Sent in " + ctx.channel.name)
    ax.bar_label(bar_container, label_type='center')
    plt.savefig(str(ctx.channel.id) + '_hiscores.png', dpi=1000, bbox_inches="tight")
    with open(str(ctx.channel.id) + '_hiscores.png', "rb") as fh:
        f = discord.File(fh, filename=str(ctx.channel.id) + '_hiscores.png')
    await ctx.send(file=f)
    
@bot.command(
    description="Highscores Server", 
    help="Shows a bar graph of users across all servers I am in and how many messages they have sent.", 
    brief="Display chat highscores"
    ) 
async def highscores_server(ctx, limit=0):
    user_message_counts = {}
    data = []
    for filename in os.listdir("channels/logs/"):
        with open("channels/logs/" + filename, 'r', encoding="utf-8") as logfile:
            data += logfile.readlines()
            logfile.close()

        
    def is_username(user):
        for character in user:
            if character.isupper():
                return False
            if not (character.isalpha() or character.isdigit() or character == '.' or character == '_'):
                return False
        return True
        

    user_message_counts = {}    
    for line in data:
        try:
            user = line[0:line.find(':')]
            if is_username(user):
                if user not in user_message_counts and user != "" and len(user) <= 32:
                    user_message_counts[user] = 1
                else:
                    user_message_counts[user] += 1
        except Exception as error:
            await handle_error(error)
            
    def remove_dict_keys_if_less_than_x(dictionary,x):
        for key in dictionary:
            if dictionary[key] <= x:
                dictionary.pop(key)
                return remove_dict_keys_if_less_than_x(dictionary,x)
        return dictionary

    print(user_message_counts)
    print("printed")
    user_message_counts = remove_dict_keys_if_less_than_x(user_message_counts,limit)
    keys = list(user_message_counts.keys())
    values = list(user_message_counts.values())
    
    fig, ax = plt.subplots()
    bar_container = ax.barh(keys, values)
    ax.set_xlabel("Message Count")
    ax.set_ylabel("Username")
    ax.set_title("Messages Sent in all channels I can see")
    ax.bar_label(bar_container, label_type='center')
    plt.savefig(str(ctx.channel.id) + '_hiscores.png', dpi=1000, bbox_inches="tight")
    with open(str(ctx.channel.id) + '_hiscores.png', "rb") as fh:
        f = discord.File(fh, filename=str(ctx.channel.id) + '_hiscores.png')
    await ctx.send(file=f)
    
@bot.command(
    description="Website", 
    help="Generates a website using gpt 3.5. Usage: !website (topic)", 
    brief="Generate a website"
    )         
async def website(ctx):
    async def delete_local_pngs(local_folder):
        for filename in os.listdir(local_folder):
            if ".png" in filename:
                os.remove(local_folder + filename)
                
    async def delete_ftp_pngs(server_folder):
        client = aioftp.Client()
        await client.connect(ftp_server)
        await client.login(ftp_username, ftp_password)
        await client.change_directory(server_folder)
        for path, info in (await client.list()):
            if ".png" in path.name:
                print("Deleting", path.name)
                await client.remove(path.name)
        await client.quit()
                        
    async def extract_image_tags(code):
        count = code.count("<img")
        tags = []
        for x in range(0,count):
            index1 = code.find("<img")
            index2 = code[index1:].find(">") + index1 + 1
            img_tag = code[index1:index2]
            tags.append(img_tag)
            code = code[index2:]
        return tags
        
    async def extract_image_alt_text(tags):
        alt_texts = []
        for tag in tags:
            index1 = tag.find("alt") + 5
            index2 = tag[index1:].find("\"") + index1
            alt_text = tag[index1:index2]
            alt_texts.append(alt_text)
        return alt_texts
        
    async def generate_images(local_folder, image_list):
        url = os.getenv('stablediffusion_url')
        if url == "disabled":
            return
        file_list = []
        for image in image_list:
            filename = image.replace(" ", "").lower() + ".png"
            payload = {"prompt": image, "steps": 25}
            response = await bot.http_session.post(url=f'{url}/sdapi/v1/txt2img', json=payload)
            r = await response.json()
            for i in r['images']:
                image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
                png_payload = {"image": "data:image/png;base64," + i}
                response2 = await bot.http_session.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)
                pnginfo = PngImagePlugin.PngInfo()
                json_response = await response2.json()
                pnginfo.add_text("parameters", json_response.get("info"))
                image.save(local_folder + filename, pnginfo=pnginfo)
                file_list.append(filename)
        return file_list
    
    async def add_image_filenames(code, file_list):
        for filename in file_list:
            code = code.replace("src=\"\"", "src=\""+ filename + "\"", 1)
        return code
        



    async def upload_html_and_imgs(local_folder, server_folder):
        client = aioftp.Client()
        await client.connect(ftp_server)
        await client.login(ftp_username, ftp_password)
        await client.change_directory(server_folder)
        
        for filename in os.listdir(local_folder):
            if ".png" in filename:
                await client.upload(local_folder + filename, filename, write_into=True)
        #explicitly upload html files last!
        for filename in os.listdir(local_folder):
            if ".html" in filename:
                await client.upload(local_folder + filename, filename, write_into=True)
        await client.quit()
                    
        
    server_folder = os.getenv('ftp_ai_webpage')
    server_archive_folder = "/media/sdq1/bottlecap/www/phixxy.com/public_html/webpage-archive/"
    local_archive_folder = "websites/"
    local_folder = "tmp/webpage/"
    working_file = local_folder + "index.html"
    if not os.path.exists(local_folder):
        os.mkdir(local_folder)
    
    try:            
        await ctx.send("Please wait, this will take a long time! You will be able to view the website here: https://phixxy.com/ai-webpage/")
        with open(working_file, "w") as f:
            f.write("<!DOCTYPE html><html><head><script>setTimeout(function(){location.reload();}, 10000);</script><title>Generating Website</title><style>body {font-size: 24px;text-align: center;margin-top: 100px;}</style></head><body><p>This webpage is currently being generated. The page will refresh once it is complete. Please be patient.</p></body></html>")
        await upload_ftp(working_file, server_folder, "index.html")
        topic = ctx.message.content.split(" ", maxsplit=1)[1]
        prompt = "Generate a webpage using html and inline css. The webpage topic should be " + topic + ". Feel free to add image tags with alt text. Leave the image source blank. The images will be added later."
        code = await answer_question(prompt)

        
        await delete_local_pngs(local_folder)
        await delete_ftp_pngs(server_folder)
        
        tags = await extract_image_tags(code)
        alt_texts = await extract_image_alt_text(tags)
        file_list = await generate_images(local_folder, alt_texts)
        code = await add_image_filenames(code, file_list)
        
        with open(working_file, 'w') as f:
            f.write(code)
            f.close()
        
        await upload_html_and_imgs(local_folder, server_folder)        
        
        await ctx.send("Finished https://phixxy.com/ai-webpage/")
    except Exception as error:
        await handle_error(error)
        await ctx.send("Failed, Try again.")
        
@bot.command(
    description="Feature", 
    help="Suggest a feature. Usage: !feature (feature)", 
    brief="Suggest a feature"
    )         
async def feature(ctx):
    try:
        feature = ctx.message.content.split(" ", maxsplit=1)[1]
        with open("features.txt",'a') as f:
            f.writelines('\n' + feature)
        await ctx.send("Added " + feature)
    except Exception as error:
        await handle_error(error)

    with open("features.txt",'r') as f:
        features = f.read()
    await ctx.send(features)


@bot.command(
    description="Draw", 
    help="Generates a picture using stable diffusion and gpt 3.5. It generates a list of 10 random artistic words and feeds them into stable diffusion. Usage: !draw (amount of pictures)", 
    brief="Generate a random image"
    )         
async def draw(ctx):
    url = os.getenv('stablediffusion_url')
    if url == "disabled":
        return
    try:
        if " " in ctx.message.content:
            amount = ctx.message.content.split(" ", maxsplit=1)[1]
            if int(amount) > 4:
                await ctx.send("No, that's too many.")
                return
        else:
            amount = 1
        await ctx.send("Please be patient this may take some time!")

        choice1 = "Give me 11 keywords I can use to generate art using AI. They should all be related to one piece of art. Please only respond with the keywords and no other text. Be sure to use keywords that really describe what the art portrays. Keywords should be comma separated with no other text!"
        choice2 = "Describe a creative scene, use only one sentence"
        choice3 = "Give me comma seperated keywords describing an imaginary piece of art. Only return the keywords and no other text."
        choice4 = "Describe a unique character and an environment in one sentence"
        choice5 = "Describe a nonhuman character and an environment in one sentence"
        prompt = random.choice([choice1,choice2,choice3,choice4,choice5])
        prompt = await answer_question(prompt)
        if random.randint(0,9):
            prompt = prompt.replace("abstract, ", "")
        prompt = prompt.replace("AI, ", "")
        if "." in prompt:
            prompt = prompt.replace(".",",")
            prompt = prompt + " masterpiece, studio quality"
        else:
            prompt = prompt + ", masterpiece, studio quality"
        negative_prompt = "easynegative verybadimagenegative_v1.3"
        payload = {"prompt": prompt,"steps": 25, "negative_prompt": negative_prompt,"batch_size": amount}
        try:
            async with bot.http_session.post(url=f'{url}/sdapi/v1/txt2img', json=payload) as resp:
                r = await resp.json()
            for i in r['images']:
                image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))
                png_payload = {"image": "data:image/png;base64," + i}
                async with bot.http_session.post(url=f'{url}/sdapi/v1/png-info', json=png_payload) as resp2:
                    response2 = await resp2.json()
                pnginfo = PngImagePlugin.PngInfo()
                pnginfo.add_text("parameters", response2.get("info"))
                my_filename = "tmp/" + str(len(os.listdir("tmp/"))) + ".png"
                image.save(my_filename, pnginfo=pnginfo)
                channel_vars = await get_channel_config(ctx.channel.id)
                if channel_vars["ftp_enabled"]:
                    await upload_ftp_ai_images(my_filename, prompt)
                with open(my_filename, "rb") as fh:
                    f = discord.File(fh, filename=my_filename)
                await ctx.send(file=f)
                await ctx.send(prompt)
        except Exception as error:
            await handle_error(error)
            await ctx.send("My image generation service may not be running.")
    except Exception as error:
        await handle_error(error)
        await ctx.send('Did you mean to use !imagine?. Usage: !draw (number)')

@bot.command(
    description="Chat", 
    help="Enable or disable bot chat in this channel. Usage !chat (enable|disable)", 
    brief="Enable or disable bot chat"
    )         
async def chat(ctx, message):
    if "enable" in message:
        edit_channel_config(ctx.channel.id, "chat_enabled", True)
        await ctx.send("Chat Enabled")
    elif "disable" in message:
        edit_channel_config(ctx.channel.id, "chat_enabled", False)
        await ctx.send("Chat Disabled")
    else:
        await ctx.send("Usage: !chat (enable|disable)")
        
@bot.command(
    description="Reactions", 
    help="Enable or disable bot reactions in this channel. Usage !reactions (enable|disable)", 
    brief="Enable or disable bot reactions"
    ) 
async def reactions(ctx, message):
    if "enable" in message:
        edit_channel_config(ctx.channel.id, "react_to_msgs", True)
        await ctx.send("Reactions Enabled")
    elif "disable" in message:
        edit_channel_config(ctx.channel.id, "react_to_msgs", False)
        await ctx.send("Reactions Disabled")
    else:
        await ctx.send("Usage: !reactions (enable|disable)")       

@bot.command(
    description="View Images", 
    help="Enable or disable bot viewing images in this channel. Usage !viewimages (enable|disable)", 
    brief="Enable or disable bot viewing images"
    )         
async def viewimages(ctx, message):
    if "enable" in message:
        edit_channel_config(ctx.channel.id, "look_at_images", True)
        await ctx.send("Viewing Enabled")
    elif "disable" in message:
        edit_channel_config(ctx.channel.id, "look_at_images", False)
        await ctx.send("Viewing Disabled")
    else:
        await ctx.send("Usage: !viewimages (enable|disable)")
        
@bot.command(
    description="Commands", 
    help="Enable or disable bot commands in this channel. Usage !enable_commands (enable|disable)", 
    brief="Enable or disable bot commands"
    )         
async def enable_commands(ctx, message):
    if "disable" in message or "false" in message:
        edit_channel_config(ctx.channel.id, "commands_enabled", False)
        await ctx.send("Commands Disabled")
    else:
        edit_channel_config(ctx.channel.id, "commands_enabled", True)
        await ctx.send("Commands Enabled")

@bot.command(
    description="Topic", 
    help="Set the channel topic for the bot. Usage: !topic (topic)", 
    brief="Set channel topic"
    )         
async def topic(ctx, channel_topic):
    edit_channel_config(ctx.channel.id, "channel_topic", channel_topic)
    await ctx.send("Topic changed to " + channel_topic)
    
@bot.command(
    description="Python", 
    help="Run some python code. Imports are disabled but random is imported for you. Usage !python (codeblock)", 
    brief="Run some python code"
    ) 
async def python(ctx):
    try:
        code = ctx.message.content
        print(code.find("```"),code.rfind("```"))
        code = code[code.find("```")+3:code.rfind("```")] #Finds the code in codeblocks
        if "import" in code:
            await ctx.send("Imports not allowed")
            return 0
        if "```" in code:
            code = code.replace("```", "")
        code = "import random\nimport math\n" + code
        if len(code) == 0:
            await ctx.send('Please provide some code to run')
        else:
            folder_path = "tmp/python_temp_scripts/"
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            unique_num = str(len(os.listdir(folder_path)))
            filename = f"{folder_path}{unique_num}.py"
            with open(filename, "w") as f:
                f.write(code)
            try:
                try:
                    response = subprocess.run(["python", filename], timeout=10, capture_output=True, check=True)
                except subprocess.TimeoutExpired:
                    await ctx.send("Code took too long to run!")
                    return 0
                print("response", response.stdout.decode('utf-8'))
                if response.stdout.decode('utf-8') == "":
                    await ctx.send("No Output")
                    return 0
                await ctx.send(response.stdout.decode('utf-8'))
            except subprocess.CalledProcessError as error:
                await ctx.send(error.stderr.decode('utf-8'))
    except Exception as error:
        await handle_error(error)
        await ctx.send("Usage: !python (codeblock)")
    
    
@bot.command(
    description="FTP", 
    help="Enable or disable bot FTP to phixxy.com in this channel. Usage !ftp (enable|disable)", 
    brief="Enable or disable uploading to web"
    )         
async def ftp(ctx, message):
    if "enable" in message:
        edit_channel_config(ctx.channel.id, "ftp_enabled", True)
        await ctx.send("FTP Enabled")
    elif "disable" in message:
        edit_channel_config(ctx.channel.id, "ftp_enabled", False)
        await ctx.send("FTP Disabled")
    else:
        await ctx.send("Usage: !ftp (enable|disable)")
    
@bot.command(
    description="Personality", 
    help="Set the personality of the bot. Usage: !personality (personality)", 
    brief="Set the personality"
    )         
async def personality(ctx):
    personality_type = ctx.message.content.split(" ", maxsplit=1)[1]
    edit_channel_config(ctx.channel.id, "personality", personality_type)
    await ctx.send("Personality changed to " + personality_type)


@bot.command(
    description="Change Model", 
    help="Choose from a list of stable diffusion models.", 
    brief="Change stable diffusion model"
    ) 
async def change_model(ctx, model_choice='0'):
    model_choices = {
        '1': ("deliberate_v2.safetensors [9aba26abdf]", "DeliberateV2"),
        '2': ("flat2DAnimerge_v30.safetensors [5dd56bfa12]", "Flat2D"),
        '3': ("Anything-V3.0.ckpt [8712e20a5d]", "AnythingV3"),
        '4': ("aZovyaPhotoreal_v2.safetensors [dde3b17c05]", "PhotorealV2"),
        '5': ("Pixel_Art_V1_PublicPrompts.ckpt [0f02127697]", "Pixel Art")
    }
    url = os.getenv('stablediffusion_url')
    if url == "disabled":
        await ctx.send("This command is currently disabled")
        return

    async with bot.http_session.get(url=f'{url}/sdapi/v1/options') as response:
        config_json = await response.json()

    current_model = config_json["sd_model_checkpoint"]
    output = 'Current Model: ' + current_model + '\n'

    if model_choice in model_choices:
        model_id, model_name = model_choices[model_choice]
        if current_model != model_id:
            payload = {"sd_model_checkpoint": model_id}
            async with bot.http_session.post(url=f'{url}/sdapi/v1/options', json=payload) as response:
                output = "Changed model to: " + model_name
                await ctx.send(output)
                return
        else:
            await ctx.send(f"Already set to use {model_name}")
            return
    else:
        model_options = '\n'.join([f"{choice}: {name}" for choice, name in model_choices.items()])
        output += model_options
        await ctx.send(output)

@bot.command(
    description="Imagine", 
    help="Generate an image using stable diffusion. You can add keyword arguments to your prompt and they will be treated as stable diffusion options. Usage !imagine (topic)", 
    brief="Generate an image"
    ) 
async def imagine(ctx):
    url = os.getenv('stablediffusion_url')
    if url == "disabled":
        await ctx.send("Command is currently disabled.")
        return
    else:
        url=f"{url}/sdapi/v1/txt2img"
    prompt = ctx.message.content.split(" ", maxsplit=1)[1]
    key_value_pairs, prompt = extract_key_value_pairs(prompt)
    #negative_prompt = ""
    #negative_prompt = "badhandsv4, worst quality, lowres, EasyNegative, hermaphrodite, cropped, not in the frame, additional faces, jpeg large artifacts, jpeg small artifacts, ugly, tiling, poorly drawn hands, poorly drawn feet, poorly drawn face, out of frame, extra limbs, disfigured, deformed, body out of frame, blurry, bad anatomy, blurred, watermark, grainy, signature, cut off, draft, not finished drawing, unfinished image, bad eyes, doll, 3d, cartoon, (bad eyes:1.2), (worst quality:1.2), (low quality:1.2), bad-image-v2-39000, (bad_prompt_version2:0.8), nude, badhandv4 By bad artist -neg easynegative ng_deepnegative_v1_75t verybadimagenegative_v1.3, (Worst Quality, Low Quality:1.4), Poorly Made Bad 3D, Lousy Bad Realistic, nsfw,(worst quality, low quality:1.4), (lip, nose, tooth, rouge, lipstick, eyeshadow:1.4), ( jpeg artifacts:1.4), (depth of field, bokeh, blurry, film grain, chromatic aberration, lens flare:1.0), (1boy, abs, muscular, rib:1.0), greyscale, monochrome, dusty sunbeams, trembling, motion lines, motion blur, emphasis lines, text, title, logo, signature, child, childlike, young, easynegative, (bad-hands-5:0.8), plain background, monochrome, poorly drawn face, poorly drawn hands, watermark, censored, (mutated hands and fingers), ugly, worst quality, low quality,, nsfw,(worst quality, low quality:1.4), (lip, nose, tooth, rouge, lipstick, eyeshadow:1.4), ( jpeg artifacts:1.4), (depth of field, bokeh, blurry, film grain, chromatic aberration, lens flare:1.0), (1boy, abs, muscular, rib:1.0), greyscale, monochrome, dusty sunbeams, trembling, motion lines, motion blur, emphasis lines, text, title, logo, signature, child, childlike, young"
    negative_prompt = "(worst quality:0.8), verybadimagenegative_v1.3 easynegative, (surreal:0.8), (modernism:0.8), (art deco:0.8), (art nouveau:0.8)"
    await ctx.send("Please be patient this may take some time! Generating: " + prompt + ".")
    
    payload = {
        "prompt": prompt,
        "steps": 25,
        "negative_prompt": negative_prompt
    }
    headers = {
        'Content-Type': 'application/json'
    }
    payload = combine_dicts(payload, key_value_pairs)
    
    try:
        async with bot.http_session.post(url, headers=headers, json=payload) as resp:
            r = await resp.json()
    except Exception as error:
        await ctx.send("My image generation service may not be running.")
        await handle_error(error)
        
    for i in r['images']:
        if not os.path.isdir("users/" + str(ctx.author.id)):
            os.makedirs("users/" + str(ctx.author.id))
        
        image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
        png_payload = {"image": "data:image/png;base64," + i}
        
        try:
            async with bot.http_session.post(url, json=png_payload) as resp:
                response2 = await resp.json()
        except Exception as error:
            await ctx.send("My image generation service may not be running.")
            await handle_error(error)

        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("parameters", response2.get("info"))
        
        my_filename = "users/" + str(ctx.author.id) + '/' + str(len(os.listdir("users/" + str(ctx.author.id) + '/'))) + ".png"
        image.save(my_filename, pnginfo=pnginfo)
        
        channel_vars = await get_channel_config(ctx.channel.id)
        
        if channel_vars["ftp_enabled"]:
            await upload_ftp_ai_images(my_filename, prompt)
        
        with open(my_filename, "rb") as fh:
            f = discord.File(fh, filename=my_filename)
        
        await ctx.send(file=f)
    
@bot.command(
    description="Describe", 
    help="Get better understanding of what the bot \"sees\" when you post an image! (Runs it through CLIP) Usage !describe (image link)", 
    brief="Describe image"
    )         
async def describe(ctx):
    url = os.getenv('stablediffusion_url')
    if url == "disabled":
        await ctx.send("Command is currently disabled")
        return
    else:
        url=f"{url}/sdapi/v1/interrogate"
    try:
        if ctx.message.content.startswith("!describe "):
            file_url = ctx.message.content.split(" ", maxsplit=1)[1]
        elif ctx.message.attachments:
            file_url = ctx.message.attachments[0].url
        else:
            print("No image linked or attached.")
            return
    except Exception as error:
        await handle_error(error)
        print("Couldn't find image.")
        return
        
    async with bot.http_session.get(file_url) as response:
        imageName = "tmp/" + str(len(os.listdir("tmp/"))) + ".png"
        with open(imageName, 'wb') as out_file:
            print(f"Saving image: {imageName}")
            while True:
                chunk = await response.content.read(1024)
                if not chunk:
                    break
                out_file.write(chunk)

    img_link = my_open_img_file(imageName)
    try:
        payload = {"image": img_link}
        async with bot.http_session.post(url, json=payload) as response:
            r = await response.json()
        print(r)
        await ctx.send(r.get("caption"))
    except Exception as error:
        await handle_error(error)
        await ctx.send("My image generation service may not be running.")
        
@bot.command(
    description="Reimagine", 
    help="Reimagine an image as something else. One example is reimagining a picture as anime. This command can be hard to use. \nUsage: !reimagine (image link) (topic)\nExample: !reimagine (image link) anime", 
    brief="Reimagine an image"
    ) 
async def reimagine(ctx):
    url = os.getenv('stablediffusion_url')
    if url == "disabled":
        await ctx.send("Command is currently disabled")
        return
    try:
        if ctx.message.attachments:
            file_url = ctx.message.attachments[0].url
            prompt = ctx.message.content.split(" ", maxsplit=1)[1]
        elif ctx.message.content.startswith("!reimagine "):
            file_url = ctx.message.content.split(" ", maxsplit=2)[1]
            prompt = ctx.message.content.split(" ", maxsplit=2)[2]
        else:
            print("No image linked or attached.")
            return
    except Exception as error:
        await handle_error(error)
        print("Couldn't find image.")
        return

    key_value_pairs, prompt = extract_key_value_pairs(prompt)

    try:
        async with bot.http_session.get(file_url) as response:
            imageName = "tmp/" + str(len(os.listdir("tmp/"))) + ".png"
            with open(imageName, 'wb') as out_file:
                print(f"Saving image: {imageName}")
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    out_file.write(chunk)
                        
    except Exception as error:
        await ctx.send("My image generation service may not be running.")
        await handle_error(error)

    img_link = my_open_img_file(imageName)

    #negative_prompt = ""
    negative_prompt = "badhandsv4, worst quality, lowres, EasyNegative, hermaphrodite, cropped, not in the frame, additional faces, jpeg large artifacts, jpeg small artifacts, ugly, tiling, poorly drawn hands, poorly drawn feet, poorly drawn face, out of frame, extra limbs, disfigured, deformed, body out of frame, blurry, bad anatomy, blurred, watermark, grainy, signature, cut off, draft, not finished drawing, unfinished image, bad eyes, doll, 3d, cartoon, (bad eyes:1.2), (worst quality:1.2), (low quality:1.2), bad-image-v2-39000, (bad_prompt_version2:0.8), nude, badhandv4 By bad artist -neg easynegative ng_deepnegative_v1_75t verybadimagenegative_v1.3, (Worst Quality, Low Quality:1.4), Poorly Made Bad 3D, Lousy Bad Realistic, nsfw,(worst quality, low quality:1.4), (lip, nose, tooth, rouge, lipstick, eyeshadow:1.4), ( jpeg artifacts:1.4), (depth of field, bokeh, blurry, film grain, chromatic aberration, lens flare:1.0), (1boy, abs, muscular, rib:1.0), greyscale, monochrome, dusty sunbeams, trembling, motion lines, motion blur, emphasis lines, text, title, logo, signature, child, childlike, young, easynegative, (bad-hands-5:0.8), plain background, monochrome, poorly drawn face, poorly drawn hands, watermark, censored, (mutated hands and fingers), ugly, worst quality, low quality,, nsfw,(worst quality, low quality:1.4), (lip, nose, tooth, rouge, lipstick, eyeshadow:1.4), ( jpeg artifacts:1.4), (depth of field, bokeh, blurry, film grain, chromatic aberration, lens flare:1.0), (1boy, abs, muscular, rib:1.0), greyscale, monochrome, dusty sunbeams, trembling, motion lines, motion blur, emphasis lines, text, title, logo, signature, child, childlike, young"

    await ctx.send("Please be patient this may take some time! Generating: " + prompt + ".")

    payload = {"init_images": [img_link], "prompt": prompt, "steps": 40, "negative_prompt": negative_prompt, "denoising_strength": 0.5}
    payload = combine_dicts(payload, key_value_pairs)

    try:
        async with bot.http_session.post(url=f'{url}/sdapi/v1/img2img', json=payload) as response:
            data = await response.json()
            for i in data['images']:
                if not os.path.isdir("tmp/reimagined/"+ str(ctx.author.id)):
                    os.makedirs("tmp/reimagined/"+ str(ctx.author.id))
                image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))
                png_payload = {"image": "data:image/png;base64," + i}
                async with bot.http_session.post(url=f'{url}/sdapi/v1/png-info', json=png_payload) as resp2:
                    response2 = await resp2.json()
                    pnginfo = PngImagePlugin.PngInfo()
                    pnginfo.add_text("parameters", response2.get("info"))
                    my_filename = "tmp/" + str(len(os.listdir("tmp/"))) + ".png"
                    image.save(my_filename, pnginfo=pnginfo)
                    with open(my_filename, "rb") as fh:
                        f = discord.File(fh, filename=my_filename)
                    await ctx.send(file=f)
    except Exception as error:
        await ctx.send("My image generation service may not be running.")
        await handle_error(error)


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
    
@bot.command(
    description="Kill", 
    help="Kills the bot in event of an emergency. Only special users can do this! Usage: !kill", 
    brief="Kill the bot",
    hidden=True
    )      
async def kill(ctx):
    "Kills the bot"
    if ctx.author.id == 242018983241318410:
        exit()
    else:
        await ctx.channel.send("You don't have permission to do that.")
        
@bot.command(
    description="Reset", 
    help="Resets the bot in event of an emergency. Only special users can do this! Usage: !reset", 
    brief="Reset the bot",
    hidden=True
    )  
async def reset(ctx):
    if ctx.author.id == 242018983241318410:
        python = sys.executable
        os.execl(python, python, *sys.argv)
    else:
        await ctx.channel.send("You don't have permission to do that.")
        
@bot.event
async def on_reaction_add(reaction, user):
    if not random.randint(0,9):
        message = reaction.message
        emoji = reaction.emoji
        await message.add_reaction(emoji)
    
        
@bot.event
async def on_message(ctx):
    logfile = "channels/logs/{0}.log".format(str(ctx.channel.id))
    channel_vars = await get_channel_config(ctx.channel.id)

    await react_to_msg(ctx, channel_vars["react_to_msgs"]) #emoji reactions
    chat_history_string = await log_chat_and_get_history(ctx, logfile, channel_vars)

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
