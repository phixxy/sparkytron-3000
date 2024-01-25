import os
import io
import base64
import time
import html
import asyncssh
from PIL import Image, PngImagePlugin
from discord.ext import commands, tasks

class PhixxyCom(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.SERVER = os.getenv('ftp_server')
        self.USERNAME = os.getenv('ftp_username')
        self.PASSWORD = os.getenv('ftp_password')
        self.working_dir = "tmp/phixxy.com/"
        self.data_dir = "data/phixxy.com/"
        self.folder_setup()
        self.stable_diffusion_log = "data/stable_diffusion/stable_diffusion.log"
        self.phixxy_loop.start()
        self.blog_loop.start()

    def folder_setup(self):
        try:
            if not os.path.exists(self.working_dir):
                os.mkdir(self.working_dir)
            if not os.path.exists(self.data_dir):
                os.mkdir(self.data_dir)
        except:
            self.bot.logger.exception("PhixxyCom failed to make directories")

    def find_prompt_from_filename(self, sd_log, filename):
        with open(sd_log, 'r') as f:
            lines = f.readlines()
            for line in reversed(lines):
                if filename in line:
                    prompt = line[line.index("Prompt: ") + 7:line.index("Filename: ")]
                    prompt = ''.join(prompt.rsplit(',', 1)) # Remove the last comma
                    return html.escape(prompt)
        return "Unknown Prompt"

    async def upload_sftp(self, local_filename, server_folder, server_filename):
        remotepath = server_folder + server_filename
        async with asyncssh.connect(self.SERVER, username=self.USERNAME, password=self.PASSWORD) as conn:
            async with conn.start_sftp_client() as sftp:
                await sftp.put(local_filename, remotepath=remotepath)

    async def delete_local_pngs(self, local_folder):
        for filename in os.listdir(local_folder):
            if ".png" in filename:
                os.remove(local_folder + filename)
    
    async def delete_ftp_pngs(self,server_folder):
        async with asyncssh.connect(os.getenv('ftp_server'), username=os.getenv('ftp_username'), password=os.getenv('ftp_password')) as conn:
            async with conn.start_sftp_client() as sftp:
                for filename in (await sftp.listdir(server_folder)):
                    if '.png' in filename:
                        try:
                            self.bot.logger.debug("Deleting", filename)
                            await sftp.remove(server_folder+filename)
                        except:
                            self.bot.logger.exception("Couldn't delete", filename)
                        
    async def extract_image_tags(self,code):
        count = code.count("<img")
        tags = []
        for x in range(0,count):
            index1 = code.find("<img")
            index2 = code[index1:].find(">") + index1 + 1
            img_tag = code[index1:index2]
            tags.append(img_tag)
            code = code[index2:]
        return tags
        
    async def extract_image_alt_text(self,tags):
        alt_texts = []
        for tag in tags:
            index1 = tag.find("alt") + 5
            index2 = tag[index1:].find("\"") + index1
            alt_text = tag[index1:index2]
            alt_texts.append(alt_text)
        return alt_texts
        
    async def generate_images(self, local_folder, image_list):
        url = os.getenv('stablediffusion_url')
        if url == "disabled":
            return
        file_list = []
        for image in image_list:
            filename = image.replace(" ", "").lower() + ".png"
            payload = {"prompt": image, "steps": 25}
            response = await self.bot.http_session.post(url=f'{url}/sdapi/v1/txt2img', json=payload)
            r = await response.json()
            for i in r['images']:
                image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
                png_payload = {"image": "data:image/png;base64," + i}
                response2 = await self.bot.http_session.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)
                pnginfo = PngImagePlugin.PngInfo()
                json_response = await response2.json()
                pnginfo.add_text("parameters", json_response.get("info"))
                image.save(local_folder + filename, pnginfo=pnginfo)
                file_list.append(filename)
        return file_list
    
    async def add_image_filenames(self, code, file_list):
        for filename in file_list:
            code = code.replace("src=\"\"", "src=\""+ filename + "\"", 1)
        return code

    async def upload_html_and_imgs(self, local_folder):

        for filename in os.listdir(local_folder):
            if ".png" in filename:
                await self.upload_sftp(local_folder + filename, (os.getenv('ftp_public_html') + 'ai-webpage/'), filename)
        #explicitly upload html files last!
        for filename in os.listdir(local_folder):
            if ".html" in filename:
                await self.upload_sftp(local_folder + filename, (os.getenv('ftp_public_html') + 'ai-webpage/'), filename)

    async def delete_derp_files(self, server_folder):
        async with asyncssh.connect(self.SERVER, username=self.USERNAME, password=self.PASSWORD) as conn:
            async with conn.start_sftp_client() as sftp:
                for filename in (await sftp.listdir(server_folder)):
                    if filename == '.' or filename == '..' or filename == 'style.css' or filename == 'myScript.js':
                        pass
                    else:
                        try:
                            self.bot.logger.debug("Deleting", filename)
                            await sftp.remove(server_folder+filename)
                        except:
                            self.bot.logger.exception("Couldn't delete", filename)

    async def meme_handler(self, folder):
        for file in os.listdir(folder):
            filepath = folder + file
            await self.update_meme_webpage(filepath)

    async def update_meme_webpage(self, filename):
        server_folder = (os.getenv('ftp_public_html') + 'ai-memes/')
        new_file_name = str(time.time_ns()) + ".png"
        await self.upload_sftp(filename, server_folder, new_file_name)
        self.bot.logger.debug("Uploaded", new_file_name)
        with open(f"{self.data_dir}ai-memes/index.html", 'r') as f:
            html_data = f.read()
        html_insert = '<!--ADD IMG HERE-->\n        <img src="' + new_file_name + '" loading="lazy">'
        html_data = html_data.replace('<!--ADD IMG HERE-->',html_insert)
        with open(f"{self.data_dir}ai-memes/index.html", "w") as f:
            f.writelines(html_data)
        await self.upload_sftp(f"{self.data_dir}ai-memes/index.html", server_folder, "index.html")
        os.rename(filename, 'tmp/' + new_file_name)

    async def upload_ftp_ai_images(self, folder):
        for filename in os.listdir(folder):
            if filename[-4:] == '.png':
                filepath = folder + filename
                prompt = self.find_prompt_from_filename(self.stable_diffusion_log, filename)
                html_file = f"{self.data_dir}ai-images/index.html"
                html_insert = '''<!--REPLACE THIS COMMENT-->
                    <div>
                        <img src="<!--filename-->" loading="lazy">
                        <p class="image-description"><!--description--></p>
                    </div>'''
                server_folder = (os.getenv('ftp_public_html') + 'ai-images/')
                new_filename = str(time.time_ns()) + ".png"
                await self.upload_sftp(filepath, server_folder, new_filename)
                self.bot.logger.debug("Uploaded", new_filename)
                with open(html_file, 'r') as f:
                    html_data = f.read()
                html_insert = html_insert.replace("<!--filename-->", new_filename)
                html_insert = html_insert.replace("<!--description-->", prompt)
                html_data = html_data.replace("<!--REPLACE THIS COMMENT-->", html_insert)
                with open(html_file, "w") as f:
                    f.writelines(html_data)
                await self.upload_sftp(html_file, server_folder, "index.html")
                os.rename(filepath, f"tmp/{new_filename}")

    async def answer_question(self, topic, model="gpt-3.5-turbo"):
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
            async with self.bot.http_session.post(url, headers=headers, json=data) as resp:
                response_data = await resp.json()
                response = response_data['choices'][0]['message']['content']
                return response

        except Exception as error:
            return None

    @commands.command()
    async def generate_blog(self):
        start_time = time.time()
        topic = ''
        filename = f"{self.data_dir}ai-blog/index.html"
        with open(filename, 'r', encoding="utf-8") as f:
            html_data = f.read()
        current_time = time.time()
        current_struct_time = time.localtime(current_time)
        date = time.strftime("%B %d, %Y", current_struct_time)
        if date in html_data:
            return
        blogpost_file = f"{self.data_dir}blog_topics.txt"
        if os.path.isfile(blogpost_file):
            with open(blogpost_file, 'r') as f:
                blogpost_topics = f.read()
                f.seek(0)
                topic = f.readline()
                blogpost_topics = blogpost_topics.replace(topic, '')
            with open(blogpost_file, 'w') as f:
                f.write(blogpost_topics)
        if topic != '':
            self.bot.logger.info("Writing blogpost")
        else:
            self.bot.logger.info("No topic given for blogpost, generating one.")
            topic = await self.answer_question("Give me one topic for an absurd blogpost.")
            
        
        post_div = '''<!--replace this with a post-->
                <div class="post">
                    <h2 class="post-title"><!--POST_TITLE--></h2>
                    <p class="post-date"><!--POST_DATE--></p>
                    <div class="post-content">
                        <!--POST_CONTENT-->
                    </div>
                </div>'''
        title_prompt = 'generate an absurd essay title about ' + topic
        title = await self.answer_question(title_prompt, model="gpt-3.5-turbo")
        prompt = 'Write a satirical essay with a serious tone titled: "' + title + '". Do not label parts of the essay.'
        content = await self.answer_question(prompt, model="gpt-4")
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
        await self.upload_sftp(filename, (os.getenv('ftp_public_html') + 'ai-blog/'), "index.html")
        run_time = time.time() - start_time
        self.bot.logger.debug("It took " + str(run_time) + " seconds to generate the blog post!")
        output = "Blog Updated! (" + str(run_time) + " seconds) https://ai.phixxy.com/ai-blog"
        return output

    @commands.command(
        description="Website", 
        help="Generates a website using gpt 3.5. Usage: !website (topic)", 
        brief="Generate a website"
        )         
    async def website(self, ctx):
        server_folder = os.getenv('ftp_public_html') + 'ai-webpage/'
        local_folder = f"{self.working_dir}/webpage/"
        working_file = local_folder + "index.html"
        if not os.path.exists(local_folder):
            os.mkdir(local_folder)
        try:            
            await ctx.send("Please wait, this will take a long time! You will be able to view the website here: https://ai.phixxy.com/ai-webpage/")
            with open(working_file, "w") as f:
                f.write("<!DOCTYPE html><html><head><script>setTimeout(function(){location.reload();}, 10000);</script><title>Generating Website</title><style>body {font-size: 24px;text-align: center;margin-top: 100px;}</style></head><body><p>This webpage is currently being generated. The page will refresh once it is complete. Please be patient.</p></body></html>")
            await self.upload_sftp(working_file, server_folder, "index.html")
            topic = ctx.message.content.split(" ", maxsplit=1)[1]
            prompt = "Generate a webpage using html and inline css. The webpage topic should be " + topic + ". Feel free to add image tags with alt text. Leave the image source blank. The images will be added later."
            code = await self.answer_question(prompt)

            
            await self.delete_local_pngs(local_folder)
            await self.delete_ftp_pngs(server_folder)
            
            tags = await self.extract_image_tags(code)
            alt_texts = await self.extract_image_alt_text(tags)
            file_list = await self.generate_images(local_folder, alt_texts)
            code = await self.add_image_filenames(code, file_list)
            
            with open(working_file, 'w') as f:
                f.write(code)
                f.close()
            
            await self.upload_html_and_imgs(local_folder)        
            
            await ctx.send("Finished https://ai.phixxy.com/ai-webpage/")
        except Exception as error:
            #await ctx.send("Failed, Try again.")
            self.bot.logger.exception("Website Error")

    @tasks.loop(seconds=60)
    async def phixxy_loop(self):
        current_time = time.localtime()
        await self.meme_handler('tmp/meme/')
        await self.upload_ftp_ai_images('tmp/stable_diffusion/sfw/')

    @tasks.loop(hours=1)
    async def blog_loop(self):
        try:
            message = await self.generate_blog()
            bot_stuff_channel = self.bot.get_channel(544408659174883328)
            await bot_stuff_channel.send(message)
        except Exception as error:
            self.bot.logger.exception("Failed to generate blog")

    @commands.command(
    description="Moderate", 
    help="This currently tool works by replacing the filename on the ftp server with a black image. The description will remain the same and may need to be altered.", 
    brief="Moderation Tools"
    )
    async def moderate(self, ctx, filename):
        await self.upload_sftp(f"{self.data_dir}blank_image.png", (os.getenv('ftp_public_html') + 'ai-images/'), filename)
        output = "Image " + filename + " replaced"
        await ctx.send(output)

async def setup(bot):
    await bot.add_cog(PhixxyCom(bot))