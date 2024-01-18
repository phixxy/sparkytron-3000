#plugin file for sparkytron 3000
import io
import base64
import aiohttp
import os
import time
import random
from PIL import Image, PngImagePlugin

from discord.ext import commands
import discord

async def answer_question(topic, model="gpt-3.5-turbo"): # Only needed for draw command
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
        return await handle_error(error)

async def handle_error(error):
    print(error)
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log_line = current_time + ': ' + str(error) + '\n'
    with open("databases/error_log.txt", 'a') as f:
        f.write(log_line)
    return error


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
                
                http_session = aiohttp.ClientSession()
                async with http_session.get(attachment.url) as response:
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
                        async with http_session.post(f'{url}/sdapi/v1/interrogate', json=payload) as response:
                            data = await response.json()
                            description = data.get("caption")
                            description = description.split(',')[0]
                            metadata += f"<image:{description}>\n"
                    except aiohttp.ClientError as error:
                        await handle_error(error)
                        return "ERROR: CLIP may not be running. Could not look at image."
    await http_session.close()
    return metadata

@commands.command(
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
            http_session = aiohttp.ClientSession()
            async with http_session.post(url=f'{url}/sdapi/v1/txt2img', json=payload) as resp:
                r = await resp.json()
            for i in r['images']:
                image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))
                png_payload = {"image": "data:image/png;base64," + i}
                async with http_session.post(url=f'{url}/sdapi/v1/png-info', json=png_payload) as resp2:
                    response2 = await resp2.json()
                pnginfo = PngImagePlugin.PngInfo()
                pnginfo.add_text("parameters", response2.get("info"))
                try:
                    if ctx.channel.is_nsfw():
                        folder = "tmp/nsfw/"
                    else:
                        folder = "tmp/sfw/"
                except:
                    folder = "tmp/"
                my_filename = folder + str(time.time_ns()) + ".png"
                image.save(my_filename, pnginfo=pnginfo)
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
    await http_session.close()

@commands.command(
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
        '5': ("Pixel_Art_V1_PublicPrompts.ckpt [0f02127697]", "Pixel Art"),
        '6': ("mistoonAnime_v20.safetensors [c35e1054c0]", "Mistoon AnimeV2")
    }
    url = os.getenv('stablediffusion_url')
    if url == "disabled":
        await ctx.send("This command is currently disabled")
        return

    http_session = aiohttp.ClientSession()
    async with http_session.get(url=f'{url}/sdapi/v1/options') as response:
        config_json = await response.json()

    current_model = config_json["sd_model_checkpoint"]
    output = 'Current Model: ' + current_model + '\n'

    if model_choice in model_choices:
        model_id, model_name = model_choices[model_choice]
        if current_model != model_id:
            payload = {"sd_model_checkpoint": model_id}
            async with http_session.post(url=f'{url}/sdapi/v1/options', json=payload) as response:
                output = "Changed model to: " + model_name
                await ctx.send(output)
                return
        else:
            await ctx.send(f"Already set to use {model_name}")
            await http_session.close()
            return
    else:
        output = '\n'.join([f"{choice}: {name}" for choice, name in model_choices.items()])
        await http_session.close()
        await ctx.send(output)
        
@commands.command(
    description="Lora", 
    help="List the stable diffusion loras.", 
    brief="List the stable diffusion loras"
    ) 
async def lora(ctx):
    lora_choices = {
        '0': ("Lora Name", "Trigger Words"),
        '1': ("<lora:rebecca:1>", "rebecca (cyberpunk)"),
        '2': ("<lora:lucy:1>", "lucy (cyberpunk)"),
        '3': ("<lora:dirty:1>", "dirty"),
        '4': ("<lora:starcraft:1>", "c0nst3llation")
    }
    output = ""
    lora_options = '\n'.join([f"{choice}: {name}" for choice, name in lora_choices.items()])
    output += lora_options
    await ctx.send(output)

@commands.command(
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
    neg_prompt_file = "databases/negative_prompt.txt"
    with open(neg_prompt_file, 'r') as f:
        negative_prompt = f.readline()
    await ctx.send("Please be patient this may take some time! Generating: " + prompt + ".")
    
    payload = {
        "prompt": prompt,
        "steps": 25,
        "negative_prompt": negative_prompt
    }
    headers = {
        'Content-Type': 'application/json'
    }
    payload.update(key_value_pairs)
    http_session = aiohttp.ClientSession()
    try:
        async with http_session.post(url, headers=headers, json=payload) as resp:
            r = await resp.json()
    except Exception as error:
        await ctx.send("My image generation service may not be running.")
        await handle_error(error)
        
    for i in r['images']:
        image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
        png_payload = {"image": "data:image/png;base64," + i}
        
        try:
            async with http_session.post(url, json=png_payload) as resp:
                response2 = await resp.json()
        except Exception as error:
            await ctx.send("My image generation service may not be running.")
            await handle_error(error)

        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("parameters", response2.get("info"))
        try:
            if ctx.channel.is_nsfw():
                folder = "tmp/"
            else:
                folder = "tmp/sfw/"
        except:
            folder = "users/" + str(ctx.author.id) + '/'
        my_filename = folder + str(time.time_ns()) + ".png"
        image.save(my_filename, pnginfo=pnginfo)
        
        with open(my_filename, "rb") as fh:
            f = discord.File(fh, filename=my_filename)
        log_data = {'Author': ctx.author.name, 'Prompt': prompt, "Filename":my_filename}
        with open("databases/stable_diffusion.log", 'a') as log_file:
            log_file.writelines(list(log_data))
        await ctx.send(f'Generated by: {ctx.author.name}\nPrompt: {prompt}', file=f)
    await http_session.close()
            
    
    
@commands.command(
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

    http_session = aiohttp.ClientSession()    
    async with http_session.get(file_url) as response:
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
        async with http_session.post(url, json=payload) as response:
            r = await response.json()
        print(r)
        await ctx.send(r.get("caption"))
    except Exception as error:
        await handle_error(error)
        await ctx.send("My image generation service may not be running.")
    await http_session.close()
        
@commands.command(
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
    http_session = aiohttp.ClientSession()
    try:
        async with http_session.get(file_url) as response:
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

    negative_prompt = "badhandsv4, worst quality, lowres, EasyNegative, hermaphrodite, cropped, not in the frame, additional faces, jpeg large artifacts, jpeg small artifacts, ugly, tiling, poorly drawn hands, poorly drawn feet, poorly drawn face, out of frame, extra limbs, disfigured, deformed, body out of frame, blurry, bad anatomy, blurred, watermark, grainy, signature, cut off, draft, not finished drawing, unfinished image, bad eyes, doll, 3d, cartoon, (bad eyes:1.2), (worst quality:1.2), (low quality:1.2), bad-image-v2-39000, (bad_prompt_version2:0.8), nude, badhandv4 By bad artist -neg easynegative ng_deepnegative_v1_75t verybadimagenegative_v1.3, (Worst Quality, Low Quality:1.4), Poorly Made Bad 3D, Lousy Bad Realistic, nsfw,(worst quality, low quality:1.4), (lip, nose, tooth, rouge, lipstick, eyeshadow:1.4), ( jpeg artifacts:1.4), (depth of field, bokeh, blurry, film grain, chromatic aberration, lens flare:1.0), (1boy, abs, muscular, rib:1.0), greyscale, monochrome, dusty sunbeams, trembling, motion lines, motion blur, emphasis lines, text, title, logo, signature, child, childlike, young, easynegative, (bad-hands-5:0.8), plain background, monochrome, poorly drawn face, poorly drawn hands, watermark, censored, (mutated hands and fingers), ugly, worst quality, low quality,, nsfw,(worst quality, low quality:1.4), (lip, nose, tooth, rouge, lipstick, eyeshadow:1.4), ( jpeg artifacts:1.4), (depth of field, bokeh, blurry, film grain, chromatic aberration, lens flare:1.0), (1boy, abs, muscular, rib:1.0), greyscale, monochrome, dusty sunbeams, trembling, motion lines, motion blur, emphasis lines, text, title, logo, signature, child, childlike, young"

    await ctx.send("Please be patient this may take some time! Generating: " + prompt + ".")

    payload = {"init_images": [img_link], "prompt": prompt, "steps": 40, "negative_prompt": negative_prompt, "denoising_strength": 0.5}
    payload.update(key_value_pairs)

    try:
        async with http_session.post(url=f'{url}/sdapi/v1/img2img', json=payload) as response:
            data = await response.json()
            for i in data['images']:
                if not os.path.isdir("tmp/reimagined/"+ str(ctx.author.id)):
                    os.makedirs("tmp/reimagined/"+ str(ctx.author.id))
                image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))
                png_payload = {"image": "data:image/png;base64," + i}
                async with http_session.post(url=f'{url}/sdapi/v1/png-info', json=png_payload) as resp2:
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
    await http_session.close()


async def setup(bot):
    bot.add_command(imagine)
    bot.add_command(reimagine)
    bot.add_command(describe)
    bot.add_command(change_model)
    bot.add_command(lora)
    bot.add_command(draw)