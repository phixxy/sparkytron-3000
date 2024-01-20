#sparkytron 3000 plugin
import os
import time
from PIL import Image, PngImagePlugin
import io
import base64

import aiohttp
import asyncssh
from discord.ext import commands, tasks

class AsyncOpenAI(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.API_KEY = os.getenv("openai.api_key")
        self.working_dir = "tmp/open_ai/"
        self.data_dir = "data/open_ai/"
        self.folder_setup()

    def folder_setup(self):
        try:
            if not os.path.exists(self.working_dir):
                os.mkdir(self.working_dir)
            if not os.path.exists(self.data_dir):
                os.mkdir(self.data_dir)
        except:
            print("AsyncOpenAI failed to make directories")

    async def handle_error(self, error):
        print(error)
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_line = current_time + ': ' + str(error) + '\n'
        with open("databases/error_log.txt", 'a') as f:
            f.write(log_line)
        return error

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
            http_session = aiohttp.ClientSession()
            async with http_session.post(url, headers=headers, json=data) as resp:
                response_data = await resp.json()
                response = response_data['choices'][0]['message']['content']
                await http_session.close()
                return response

        except Exception as error:
            return await self.handle_error(error)

    @commands.command(
        description="Blog", 
        help="Adds your topic to the list of possible future blog topics. Usage: !suggest_blog (topic)", 
        brief="Suggest a blog topic"
        )
    async def blog(self, ctx, *args):
        message = ' '.join(args)
        if '\n' in message:
            await ctx.send("Send only one topic at a time.")
            return
        else:
            blogpost_file = "databases/blog_topics.txt"
            with open(blogpost_file, 'a') as f:
                f.writelines(message+'\n')
            await ctx.send("Saved suggestion!")

    @commands.command(
        description="Question", 
        help="Ask a raw chatgpt question. Usage: !question (question)", 
        brief="Get an answer"
        )        
    async def question(self, ctx):
        question = ctx.message.content.split(" ", maxsplit=1)[1]
        answer = await self.answer_question(question)
        chunks = [answer[i:i+1999] for i in range(0, len(answer), 1999)]
        for chunk in chunks:
            await ctx.send(chunk)
            
    @commands.command(
        description="Question GPT4", 
        help="Ask GPT4 a question. Usage: !question_gpt4 (question)", 
        brief="Get an answer"
        )         
    async def question_gpt4(self, ctx):
        question = ctx.message.content.split(" ", maxsplit=1)[1]
        answer = await self.answer_question(question, "gpt-4-vision-preview")
        chunks = [answer[i:i+1999] for i in range(0, len(answer), 1999)]
        for chunk in chunks:
            await ctx.send(chunk)
            
    @commands.command(
        description="Image GPT4", 
        help="Ask GPT4 a question about an image. Usage: !question_gpt4 (link) (question)", 
        brief="Get an answer"
        )         
    async def looker(self, ctx):
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
            return await self.handle_error(error)
        
        chunks = [answer[i:i+1999] for i in range(0, len(answer), 1999)]
        for chunk in chunks:
            await ctx.send(chunk)

async def setup(bot):
    bot.add_cog(AsyncOpenAI)