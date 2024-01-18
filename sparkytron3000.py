import discord
from discord.ext import commands, tasks
from discord.utils import get
import shutil
import json
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

@bot.command(
    description="Moderate", 
    help="This currently tool works by replacing the filename on the ftp server with a black image. The description will remain the same and may need to be altered.", 
    brief="Moderation Tools"
    )
async def moderate(ctx, filename):
    await upload_sftp("blank_image.png", (os.getenv('ftp_public_html') + 'ai-images/'), filename)
    output = "Image " + filename + " replaced"
    await ctx.send(output)
    
async def upload_ftp(local_filename, server_folder, server_filename):
    client = aioftp.Client()
    await client.connect(ftp_server)
    await client.login(ftp_username, ftp_password)
    await client.change_directory(server_folder)
    await client.upload(local_filename, server_folder+server_filename, write_into=True)
    await client.quit()

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
    

async def upload_ftp_ai_images(filename, prompt):
    html_file = "phixxy.com/ai-images/index.html"
    html_insert = '''<!--REPLACE THIS COMMENT-->
        <div>
            <img src="<!--filename-->" loading="lazy">
            <p class="image-description"><!--description--></p>
        </div>'''
    img_list = []
    server_folder = (os.getenv('ftp_public_html') + 'ai-images/')
    new_filename = str(time.time_ns()) + ".png"
    await upload_sftp(filename, server_folder, new_filename)
    print("Uploaded", new_filename)
    with open(html_file, 'r') as f:
        html_data = f.read()
    html_insert = html_insert.replace("<!--filename-->", new_filename)
    html_insert = html_insert.replace("<!--description-->", prompt)
    html_data = html_data.replace("<!--REPLACE THIS COMMENT-->", html_insert)
    with open(html_file, "w") as f:
        f.writelines(html_data)
    await upload_sftp(html_file, server_folder, "index.html")

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


def edit_channel_config(channel_id, key, value):
    config_file = "channels/config/" + str(channel_id) + ".json"
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    config_data[key] = value
    with open(config_file, "w") as f:
        json.dump(config_data, f)
        
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
    #metadata = await look_at(ctx, channel_vars["look_at_images"])
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
            await ctx.send("Update Attempted")
            await ctx.send(output.stderr.decode('utf-8'))
        else:
            await ctx.send(output.stdout.decode('utf-8'))
    else:
        await ctx.send("You don't have permission to do this.")
        
        
@bot.command(
    description="Errors", 
    help="Shows the last errors that were logged.", 
    brief="Display Errors"
    )       
async def errors(ctx, amount="5"):
    output = ""
    amount = int(amount)
    try:
        with open("databases/error_log.txt", 'r') as f:
            for line in (f.readlines() [-amount:]):
                output += line
        await ctx.send(output)
    except Exception as error:
        await handle_error(error)
        
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
    output += str(amount) + ' osrs gp would cost: $' + str(round(osrwtcost,2)) + " (RWT)\n"
    output += str(amount) + ' rs3 gp would cost: $' + str(round(bondcost,2)) + " (Bonds)\n"
    output += str(amount) + ' osrs gp would cost: $' + str(round(osbondcost,2)) + " (Bonds)\n"
    output += str(amount) + ' dollars spent on rs3 gp would be: ' + str(round(dollar_gp,2)) + " (RS3 GP)\n"
    output += str(amount) + ' dollars spent on osrs gp would be: ' + str(round(osdollar_gp,2)) + " (OSRS GP)\n"
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
        
@bot.command(
    description="Negative Prompt", 
    help="Changes the negative prompt for imagine across all channels", 
    brief="Change the negative prompt for imagine"
    )
async def negative_prompt(ctx, *args):
    message = ' '.join(args)
    if not message:
        message = "easynegative, badhandv4, verybadimagenegative_v1.3"
    neg_prompt_file = "databases/negative_prompt.txt"
    with open(neg_prompt_file, 'w') as f:
        f.writelines(message)
    await ctx.send("Changed negative prompt to " + message)

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
    #blog_subscribers = ["276197608735637505","242018983241318410"]
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
    
    
    await upload_sftp(filename, (os.getenv('ftp_public_html') + 'ai-blog/'), "index.html")
    run_time = time.time() - start_time
    print("It took " + str(run_time) + " seconds to generate the blog post!")
    output = "Blog Updated! (" + str(run_time) + " seconds) https://ai.phixxy.com/ai-blog"
    #output += '\nNotifying subscribers: '
    #for subscriber in blog_subscribers:
    #    output += '<@' + subscriber + '> '
    await ctx.send(output)

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
        os.rename(filename, f'tmp/{filename}')


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
    answer = await answer_question(question, "gpt-4-vision-preview")
    chunks = [answer[i:i+1999] for i in range(0, len(answer), 1999)]
    for chunk in chunks:
        await ctx.send(chunk)
        
@bot.command(
    description="Image GPT4", 
    help="Ask GPT4 a question about an image. Usage: !question_gpt4 (link) (question)", 
    brief="Get an answer"
    )         
async def looker(ctx):
    image_link = ctx.message.content.split(" ", maxsplit=2)[1]
    question = ctx.message.content.split(" ", maxsplit=2)[2]
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.getenv("openai.api_key")}',
    }

    data = {
        "model": "gpt-4-vision-preview",
        "messages": [{"role": "user", "content": [{"type": "text", "text": question},{"type": "image_url","image_url": {"url": image_link}}]}],
        "max_tokens": 500
    }

    url = "https://api.openai.com/v1/chat/completions"

    try:
        async with bot.http_session.post(url, headers=headers, json=data) as resp:
            response_data = await resp.json()
            print(response_data)
            answer = response_data['choices'][0]['message']['content']
        

    except Exception as error:
        return await handle_error(error)
    
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
        async with asyncssh.connect(ftp_server, username=ftp_username, password=ftp_password) as conn:
            async with conn.start_sftp_client() as sftp:
                for filename in (await sftp.listdir(server_folder)):
                    if '.png' in filename:
                        try:
                            print("Deleting", filename)
                            await sftp.remove(server_folder+filename)
                        except:
                            print("Couldn't delete", filename)
                        
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

        for filename in os.listdir(local_folder):
            if ".png" in filename:
                await upload_sftp(local_folder + filename, (os.getenv('ftp_public_html') + 'ai-webpage/'), filename)
        #explicitly upload html files last!
        for filename in os.listdir(local_folder):
            if ".html" in filename:
                await upload_sftp(local_folder + filename, (os.getenv('ftp_public_html') + 'ai-webpage/'), filename)
                    
        
    server_folder = ftp_public_html + 'ai-webpage/'
    server_archive_folder = ftp_public_html + "webpage-archive/"
    local_archive_folder = "websites/"
    local_folder = "tmp/webpage/"
    working_file = local_folder + "index.html"
    if not os.path.exists(local_folder):
        os.mkdir(local_folder)
    
    try:            
        await ctx.send("Please wait, this will take a long time! You will be able to view the website here: https://ai.phixxy.com/ai-webpage/")
        with open(working_file, "w") as f:
            f.write("<!DOCTYPE html><html><head><script>setTimeout(function(){location.reload();}, 10000);</script><title>Generating Website</title><style>body {font-size: 24px;text-align: center;margin-top: 100px;}</style></head><body><p>This webpage is currently being generated. The page will refresh once it is complete. Please be patient.</p></body></html>")
        await upload_sftp(working_file, server_folder, "index.html")
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
        
        await ctx.send("Finished https://ai.phixxy.com/ai-webpage/")
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
    
'''@bot.command(
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
        await ctx.send("Usage: !python (codeblock)")'''
    
    
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
    
'''@bot.command(
    description="Secret Santa Register", 
    help="Register for secret santa!", 
    brief="Register for secret santa!"
    )         
async def ss_register(ctx):
    try:
        email = ctx.message.content.split(" ", maxsplit=1)[1]
        print(ctx.author.name, email)
        with open("santa.txt", 'a') as f:
            f.writelines(ctx.author.name + ';' + email + ',')
        await ctx.send(ctx.author.name + " registered for secret santa!")
    except:
        await ctx.send("Usage: !ss_register (email address)")'''


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
