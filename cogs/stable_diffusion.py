# This extension enables the ability to generate AI artwork using the AUTOMATIC1111 API
import io
import logging
import base64
import os
import time
import random
from PIL import Image, PngImagePlugin
import aiohttp
import discord
from discord.ext import commands


class StableDiffusion(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.stable_diffusion_ip = os.getenv("stable_diffusion_ip")
        self.stable_diffusion_port = os.getenv("stable_diffusion_port")
        self.stable_diffusion_url = f"http://{self.stable_diffusion_ip}:{self.stable_diffusion_port}"
        self.working_dir = "tmp/stable_diffusion/"
        self.data_dir = "data/stable_diffusion/"
        self.default_neg_prompt = "easynegative, badhandv4, verybadimagenegative_v1.3"
        self.folder_setup()
        self.http_session = self.create_aiohttp_session()
        self.logger = logging.getLogger("bot")

    def create_aiohttp_session(self):
        return aiohttp.ClientSession()

    def folder_setup(self) -> None:
        try:
            if not os.path.exists(self.working_dir):
                os.mkdir(self.working_dir)
                os.mkdir(f"{self.working_dir}sfw")
                os.mkdir(f"{self.working_dir}nsfw")
            if not os.path.exists(self.data_dir):
                os.mkdir(self.data_dir)
        except:
            self.logger.exception("StableDiffusion failed to make directories")

    """
    answer_question asynchronously calls the OpenAI API to get a response for the given question/topic using the specified model.
    
    Parameters:
    - topic (str): The question or topic to get a response for.
    - model (str): The OpenAI model to use. Defaults to "gpt-3.5-turbo".
    
    Returns:
    - str: The response from the OpenAI API.
    
    Raises:
    - Exception: If an error occurs when calling the API.
    """
    async def answer_question(self, topic: str, model: str="gpt-3.5-turbo") -> str: # Only needed for draw command
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
                async with self.http_session.post(url, headers=headers, json=data) as resp:
                    response_data = await resp.json()
                    response = response_data['choices'][0]['message']['content']
                    return response
            except:
                return "Error in answer question in stable_diffusion"

    """
    Gets key-value pairs from a context message.
    
    Parses the message content to extract key-value pairs separated by '='. 
    Returns a dict of key-value pairs.
    
    Parameters:
        ctx (commands.Context): The context object containing the message.
    
    Returns:
        dict: A dict of key-value pairs extracted from the message.
    """
    def get_kv_from_ctx(self, ctx: commands.Context) -> dict:
            try:
                prompt = ctx.message.content.split(" ", maxsplit=1)[1]
                kv_strings = list(filter(lambda x: '=' in x,prompt.split(' ')))
                key_value_pairs = dict(map(lambda a: a.replace(',','').split('='),kv_strings))
                return key_value_pairs
            except:
                return None
    
    """
    Gets prompt from context message by splitting on spaces and removing key-value pairs.
    
    Splits the context message content on spaces, takes the second part after 
    the command name. Removes any key-value pairs separated by '=' from the prompt.
    
    Parameters:
        ctx (commands.Context): The context object containing the message.
        
    Returns:
        str: The prompt text extracted from the context message.
    """
    def get_prompt_from_ctx(self, ctx: commands.Context) -> str:
            try:
                prompt = ctx.message.content.split(" ", maxsplit=1)[1]
                prompt = ' '.join(list(filter(lambda x: '=' not in x,prompt.split(' '))))
                return prompt
            except:
                return None

    """
    Encodes an image file from the given path into a base64 string.
    
    Opens the image file, encodes it into a base64 string, closes the image, 
    and returns the encoded string.
    
    Parameters:
        path (str): The path to the image file.
    
    Returns:
        str: The base64 encoded image data.
    """
    async def my_open_img_file(self, path: str) -> str:
        img = Image.open(path)
        encoded = ""  
        with io.BytesIO() as output:
            img.save(output, format="PNG")
            contents = output.getvalue()
            encoded = str(base64.b64encode(contents), encoding='utf-8')
        img.close()
        return encoded

    """
    Looks at an image attachment in the given context and returns metadata about it.
    
    If the look parameter is True, this iterates through the attachments 
    in the context checking for image files. If an image is found, it is 
    downloaded and encoded to base64. The image is then sent to the 
    Stable Diffusion API to generate a caption, which is returned in the metadata.
    
    Parameters:
        ctx (commands.Context): The context containing the command and attachments.
        look (bool): Whether to look at images and generate metadata.
    
    Returns:
        str: The metadata string containing any generated image captions.
    """
    async def look_at(self, ctx: commands.Context, look: bool=False) -> str:
        metadata = ""
        if look:
            url = self.stable_diffusion_url
            if url == "disabled":
                return "Stable Diffusion is disabled, could not look at image"
            for attachment in ctx.attachments:
                if attachment.url.endswith(('.jpg', '.png')):
                    self.logger.debug("image seen")
                    async with self.http_session.get(attachment.url) as response:
                        imageName = self.working_dir + str(time.time_ns()) + '.png'
                        
                        with open(imageName, 'wb') as out_file:
                            self.logger.debug('Saving image: ' + imageName)
                            while True:
                                chunk = await response.content.read(1024)
                                if not chunk:
                                    break
                                out_file.write(chunk)

                        img_link = await self.my_open_img_file(imageName)
                        
                        try:
                            payload = {"image": img_link}
                            async with self.http_session.post(f'{url}/sdapi/v1/interrogate', json=payload) as response:
                                data = await response.json()
                                description = data.get("caption")
                                description = description.split(',')[0]
                                metadata += f"<image:{description}>\n"
                        except aiohttp.ClientError:
                            self.logger.exception("ERROR: CLIP may not be running. Could not look at image.")
                            return "ERROR: CLIP may not be running. Could not look at image."
        return metadata
    
    """
    Generates a prompt for use with an AI art generator.
    
    Combines randomly selected question prompts with an AI assistant's response, 
    then optionally removes abstract keywords and adds modifiers like "masterpiece" 
    to create a prompt that describes a detailed scene or character for the AI art 
    generator.
    """
    async def generate_prompt(self) -> str:
        choice1 = "Give me 11 keywords I can use to generate art using AI. They should all be related to one piece of art. Please only respond with the keywords and no other text. Be sure to use keywords that really describe what the art portrays. Keywords should be comma separated with no other text!"
        choice2 = "Describe a creative scene, use only one sentence"
        choice3 = "Give me comma seperated keywords describing an imaginary piece of art. Only return the keywords and no other text."
        choice4 = "Describe a unique character and an environment in one sentence"
        choice5 = "Describe a nonhuman character and an environment in one sentence"
        prompt = random.choice([choice1,choice2,choice3,choice4,choice5])
        prompt = await self.answer_question(prompt)
        if random.randint(0,9):
            prompt = prompt.replace("abstract, ", "")
        prompt = prompt.replace("AI, ", "")
        if "." in prompt:
            prompt = prompt.replace(".",",")
            prompt = prompt + " masterpiece, studio quality"
        else:
            prompt = prompt + ", masterpiece, studio quality"
        return prompt

    @commands.command(
        description="Change Model", 
        help="Changes the Stable Diffusion model used by the bot.", 
        brief="Change stable diffusion model"
        ) 
    async def change_model(self, ctx: commands.Context, model_choice: str='0') -> None: # Needs to be a configurable list of models
        model_choices = {
            '1': ("deliberate_v2.safetensors [9aba26abdf]", "DeliberateV2"),
            '2': ("flat2DAnimerge_v30.safetensors [5dd56bfa12]", "Flat2D"),
            '3': ("Anything-V3.0.ckpt [8712e20a5d]", "AnythingV3"),
            '4': ("aZovyaPhotoreal_v2.safetensors [dde3b17c05]", "PhotorealV2"),
            '5': ("Pixel_Art_V1_PublicPrompts.ckpt [0f02127697]", "Pixel Art"),
            '6': ("mistoonAnime_v20.safetensors [c35e1054c0]", "Mistoon AnimeV2")
        }
        url = self.stable_diffusion_url
        if url == "disabled":
            await ctx.send("This command is currently disabled")
        else:
            async with self.http_session.get(url=f'{url}/sdapi/v1/options') as response:
                config_json = await response.json()

            current_model = config_json["sd_model_checkpoint"]
            output = 'Current Model: ' + current_model + '\n'

            if model_choice in model_choices:
                model_id, model_name = model_choices[model_choice]
                if current_model != model_id:
                    payload = {"sd_model_checkpoint": model_id}
                    async with self.http_session.post(url=f'{url}/sdapi/v1/options', json=payload) as response:
                        output = "Changed model to: " + model_name
                        await ctx.send(output)
                        return
                else:
                    await ctx.send(f"Already set to use {model_name}")
                    return
            else:
                output = '\n'.join([f"{choice}: {name}" for choice, name in model_choices.items()])
                await ctx.send(output)

    @commands.command(
        description="Lora", 
        help="Lists available Stable Diffusion loras and their trigger words.", 
        brief="List the stable diffusion loras"
        ) 
    async def lora(self, ctx: commands.Context) -> None:
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

    """
    Gets the image URL from a Discord context.
    
    Checks for an image URL in attachments or message content.

    Args:
        ctx: Discord context
    
    Returns:
        str: Image URL or None
    """
    async def get_image_from_ctx(self, ctx: commands.Context) -> str:
        if ctx.message.attachments:
            file_url = ctx.message.attachments[0].url
            return file_url
        try:
            file_url = ctx.message.content.split(" ", maxsplit=1)[1]
            return file_url
        except:
            self.logger.info("Couldn't find image.")
            return None

    """
    Sends an image generation request to the Stable Diffusion API.
    
    Args:
        ctx: The Discord context.
        prompt: The text prompt to generate the image from.
    
    Returns:
        None. Sends the generated image back to the user.
    """
    async def txt2img(self, ctx: commands.Context, prompt: str) -> None:
        url = f"{self.stable_diffusion_url}/sdapi/v1/txt2img"
        key_value_pairs = self.get_kv_from_ctx(ctx)
        negative_prompt = self.get_negative_prompt()
        if negative_prompt != self.default_neg_prompt:
            await ctx.send(f"Using non-default negative prompt: {negative_prompt}")
        headers = {'Content-Type': 'application/json'}  
        payload = {
            "prompt": prompt,
            "steps": 25,
            "negative_prompt": negative_prompt 
        }
        if key_value_pairs:
            payload.update(key_value_pairs)
        try:
            async with self.http_session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    await ctx.send(f"{resp.status} {resp.reason}")
                    self.logger.exception(f"{resp.status} {resp.reason}")
                    return
                r = await resp.json()
        except ConnectionRefusedError:
            await ctx.send("Failed to connect to image generation service")
            self.logger.exception("Failed to connect to image generation service")
            return
        except:
            await ctx.send("Failed to generate image")
            self.logger.exception("Failed to generate image")
            return
        
        await self.send_generated_image(ctx, r['images'], prompt)
    
    """
    Saves an image from a URL to disk.
    
    Args:
      url: The URL of the image to save.
    
    Returns:
      The path to the saved image file.
    """
    async def save_image(self, url: str) -> str:
        async with self.http_session.get(url) as response:
            image_name = self.working_dir + str(time.time_ns()) + ".png"
            with open(image_name, 'wb') as out_file:
                self.logger.debug(f"Saving image: {image_name}")
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    out_file.write(chunk)
        return image_name

    """
    Generates an image by modifying an initial image based on an optional
    text prompt.

    Sends a request to the Stable Diffusion API to modify the initial image
    according to the given prompt. The modified image is then sent back to 
    the user.

    Args:
    ctx: The Discord context.
    prompt: The text prompt to guide image modification.

    Returns:
    None. Sends the generated image back to the user.
    """
    async def img2img(self, ctx: commands.Context, prompt: str) -> None:
        url = f"{self.stable_diffusion_url}/sdapi/v1/img2img"
        file_url = await self.get_image_from_ctx(ctx)
        image_name = await self.save_image(file_url)
        file_url = await self.my_open_img_file(image_name)
        key_value_pairs = self.get_kv_from_ctx(ctx)
        headers = {'Content-Type': 'application/json'}  
        payload = {
            "init_images": [file_url],
            "prompt": prompt,
            "steps": 40,
            "negative_prompt": self.get_negative_prompt(),
            "denoising_strength": 0.5,
        }
        if key_value_pairs:
            payload.update(key_value_pairs)
        try:
            async with self.http_session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    await ctx.send(f"{resp.status} {resp.reason}")
                    self.logger.error(f"{resp.status} {resp.reason}")
                    return
                r = await resp.json()
        except ConnectionRefusedError:
            await ctx.send("Failed to connect to image generation service")
            self.logger.exception("Failed to connect to image generation service")
            return
        except:
            await ctx.send("Failed to generate image")
            self.logger.exception("Failed to generate image")
            return
        
        await self.send_generated_image(ctx, r['images'], prompt)


    """
    Sends a generated image file to Discord along with the prompt. 
    
    Saves the image file locally first, logs the prompt and filename, 
    then sends the image and prompt to Discord.
    
    Args:
    ctx: The Discord context. 
    images: List of base64 encoded image data.
    prompt: The text prompt used to generate the image.
    
    Returns: None.
    """
    async def send_generated_image(self, ctx: commands.Context, images: dict, prompt: str) -> None:
        for i in images:
            image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
            try:
                if ctx.channel.is_nsfw():
                    folder = self.working_dir + "nsfw/"
                else:
                    folder = self.working_dir + "sfw/"
            except:
                folder = self.working_dir
            my_filename = str(time.time_ns()) + ".png"
            filepath = folder + my_filename
            image.save(filepath)
                    
            with open(filepath, "rb") as fh:
                f = discord.File(fh, filename=filepath)
            
            prompt = prompt.replace('\n',' ')
            log_data = f'Author: {ctx.author.name}, Prompt: {prompt}, Filename: {my_filename}\n'
            with open(f"{self.data_dir}stable_diffusion.log", 'a') as log_file:
                log_file.writelines(log_data)

            await ctx.send(f'Generated by: {ctx.author.name}\nPrompt: {prompt}', file=f)


    """
    Gets a negative prompt text from a file.
    
    If the file does not exist, it will be created with 
    default negative prompt text.
    
    Returns:
        str: The negative prompt text loaded from the file.
    """
    def get_negative_prompt(self) -> str:
        try:
            neg_prompt_file = f"{self.data_dir}negative_prompt.txt"
            with open(neg_prompt_file, 'r') as f:
                negative_prompt = f.readline()
        except:
            neg_prompt_file = f"{self.data_dir}negative_prompt.txt"
            with open(neg_prompt_file, 'w') as f:
                f.writelines(self.default_neg_prompt)
                negative_prompt = self.default_neg_prompt
        return negative_prompt

    @commands.command(
        description="Imagine",
        help="Generate an image using stable diffusion. You can add keyword arguments to your prompt and they will be treated as stable diffusion options. Usage !imagine (topic)",
        brief="Generate an image"
        )
    async def imagine(self, ctx: commands.Context) -> None:
        url = self.stable_diffusion_url
        if url == "disabled":
            await ctx.send("Command is currently disabled")
            return
        prompt = self.get_prompt_from_ctx(ctx)
        self.logger.info(f"{ctx.author.name} used imagine. Prompt: {prompt}")
        if prompt == None:
            prompt = await self.generate_prompt()
        
        await ctx.send(f"Please be patient this may take some time! Generating: {prompt}.")

        await self.txt2img(ctx, prompt)

        
    @commands.command(
        description="Describe", 
        help="Get better understanding of what the bot \"sees\" when you post an image! (Runs it through CLIP) Usage !describe (image link)", 
        brief="Describe image"
        )         
    async def describe(self, ctx: commands.Context) -> None:
        url = self.stable_diffusion_url
        if url == "disabled":
            await ctx.send("Command is currently disabled")
            return
        else:
            url=f"{url}/sdapi/v1/interrogate"
        file_url = await self.get_image_from_ctx(ctx)
        image_name = await self.save_image(file_url)
        img_link = await self.my_open_img_file(image_name)
        try:
            payload = {"image": img_link}
            async with self.http_session.post(url, json=payload) as response:
                r = await response.json()
            await ctx.send(r.get("caption"))
        except:
            self.logger.exception("error in describe")
            await ctx.send("My image generation service may not be running.")

    @commands.command(
        description="Reimagine", 
        help="Reimagine an image as something else. One example is reimagining a picture as anime. This command can be hard to use. \nUsage: !reimagine (image link) (topic)\nExample: !reimagine (image link) anime", 
        brief="Reimagine an image"
        ) 
    async def reimagine(self, ctx: commands.Context) -> None:
        url = self.stable_diffusion_url
        if url == "disabled":
            await ctx.send("Command is currently disabled")
            return
        prompt = self.get_prompt_from_ctx(ctx)
        if not prompt:
            prompt = ""
        await ctx.send(f"Please be patient this may take some time! Generating: {prompt}.")
        await self.img2img(ctx, prompt)
            
    @commands.command(
        description="Negative Prompt", 
        help="Changes the negative prompt for imagine across all channels", 
        brief="Change the negative prompt for imagine"
        )
    async def negative_prompt(self, ctx: commands.Context, *args: tuple) -> None:
        message = ' '.join(args)
        if not message:
            message = self.default_neg_prompt
        neg_prompt_file = f"{self.data_dir}negative_prompt.txt"
        with open(neg_prompt_file, 'w') as f:
            f.writelines(message)
        await ctx.send("Changed negative prompt to " + message)


async def setup(bot: commands.Bot):
    await bot.add_cog(StableDiffusion(bot))
    