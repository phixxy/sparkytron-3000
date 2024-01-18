#sparkytron 3000 plugin
import os
import time
from PIL import Image, PngImagePlugin
import io
import base64

import aiohttp
import asyncssh
from discord.ext import commands, tasks

async def upload_sftp(local_filename, server_folder, server_filename):
    remotepath = server_folder + server_filename
    async with asyncssh.connect(os.getenv('ftp_server'), username=os.getenv('ftp_username'), password=os.getenv('ftp_password')) as conn:
        async with conn.start_sftp_client() as sftp:
            await sftp.put(local_filename, remotepath=remotepath)

async def handle_error(error):
    print(error)
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log_line = current_time + ': ' + str(error) + '\n'
    with open("databases/error_log.txt", 'a') as f:
        f.write(log_line)
    return error

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
        return await handle_error(error)

@commands.command(
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

@commands.command()
async def generate_blog():
    start_time = time.time()
    topic = ''
    filename = "phixxy.com/ai-blog/index.html"
    with open(filename, 'r', encoding="utf-8") as f:
        html_data = f.read()
    current_time = time.time()
    current_struct_time = time.localtime(current_time)
    date = time.strftime("%B %d, %Y", current_struct_time)
    if date in html_data:
        print("I already wrote a blog post today!")
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
        print("Writing blogpost")
    else:
        print("No topic given for blogpost, generating one.")
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
    print(output)

@commands.command(
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
        
@commands.command(
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
        
@commands.command(
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
        http_session = aiohttp.ClientSession()
        async with http_session.post(url, headers=headers, json=data) as resp:
            response_data = await resp.json()
            print(response_data)
            answer = response_data['choices'][0]['message']['content']
        await http_session.close()
        

    except Exception as error:
        return await handle_error(error)
    
    chunks = [answer[i:i+1999] for i in range(0, len(answer), 1999)]
    for chunk in chunks:
        await ctx.send(chunk)

@commands.command(
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
        async with asyncssh.connect(os.getenv('ftp_server'), username=os.getenv('ftp_username'), password=os.getenv('ftp_password')) as conn:
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
            http_session = aiohttp.ClientSession()
            response = await http_session.post(url=f'{url}/sdapi/v1/txt2img', json=payload)
            r = await response.json()
            for i in r['images']:
                image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
                png_payload = {"image": "data:image/png;base64," + i}
                response2 = await http_session.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)
                pnginfo = PngImagePlugin.PngInfo()
                json_response = await response2.json()
                pnginfo.add_text("parameters", json_response.get("info"))
                image.save(local_folder + filename, pnginfo=pnginfo)
                file_list.append(filename)
        await http_session.close()
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
                    
        
    server_folder = os.getenv('ftp_public_html') + 'ai-webpage/'
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

@tasks.loop(seconds=1)
async def ai_task_loop():
    current_time = time.localtime()
    if current_time.tm_hour == 17 and current_time.tm_min == 0 and current_time.tm_sec == 0:
        try:
            await generate_blog()
        except Exception as error:
            await handle_error(error)

async def setup(bot):
    bot.add_command(question)
    bot.add_command(question_gpt4)
    bot.add_command(generate_blog)
    bot.add_command(blog)
    bot.add_command(website)
    bot.add_command(looker)
    #ai_task_loop.start() #I don't know if this will work or not