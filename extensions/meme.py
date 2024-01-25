#plugin for sparkytron3000
import os
import random
import time
import aiohttp

from discord.ext import commands

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
        http_session = aiohttp.ClientSession()
        async with http_session.post(url, headers=headers, json=data) as resp:
            response_data = await resp.json()
            response = response_data['choices'][0]['message']['content']
            await http_session.close()
            return response
    except Exception as error:
        return "error occurred in meme"

@commands.command(
    description="Meme", 
    help="Generates a meme based on input. Usage: !meme (topic)", 
    brief="Generate a meme"
    )       
async def meme(ctx):
    async def generate_random_meme(topic):
        http_session = aiohttp.ClientSession()
        async with http_session.get('https://api.imgflip.com/get_memes') as resp:
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
        imgflip_username = os.getenv('imgflip_username')
        imgflip_password = os.getenv('imgflip_password')
        params = {
            'username':imgflip_username,
            'password':imgflip_password,
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
            #http_session = aiohttp.ClientSession()
            async with http_session.post(URL, params=params) as resp:
                response = await resp.json()
            print(f"Generated Meme = {response['success']}\nImage Link = {response['data']['url']}\nPage Link = {response['data']['page_url']}")
            image_link = response['data']['url']
        except Exception as error:
            print("Error occurred in meme")
        try:
    #------------------------------------Saving Image Using Aiohttp---------------------------------#
            filename = memepics[id-1]['name']
            async with http_session.get(image_link) as response:
                folder = "tmp/meme/"
                filename = folder + topic + str(len(os.listdir(folder))) + ".jpg"
                
                with open(filename, "wb") as file:
                    while True:
                        chunk = await response.content.read(1024) # Read the response in chunks
                        if not chunk:
                            break
                        file.write(chunk)
        except Exception as error:
            print("Something's Wrong with the aiohttp in meme So try again")
        await http_session.close()
        return image_link, filename
    
    try:
        topic = ctx.message.content.split(" ", maxsplit=1)[1]
        await ctx.send(f'Generating {topic} meme')
        link, filepath = await generate_random_meme(topic)
        await ctx.send(link)
    except Exception as error:
        print("Error occurred in meme")
        await ctx.send('Something went wrong try again. Usage: !meme (topic)')

async def setup(bot):
    bot.add_command(meme)