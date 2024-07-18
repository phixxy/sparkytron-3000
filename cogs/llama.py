import os
import time
import json
import logging
import random
import asyncio
import aiofiles
import aiohttp
import discord
from discord.ext import commands, tasks

class Llama(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.bot_id = 1097302679836971038
        self.admin_id = 242018983241318410
        self.working_dir = "tmp/chatgpt/"
        self.data_dir = "data/chatgpt/"
        self.http_session = self.create_aiohttp_session()
        self.logger = logging.getLogger("bot")
        self.server = "http://192.168.0.34:11434"

        
    def create_aiohttp_session(self):
        return aiohttp.ClientSession()
    
    def folder_setup(self):
        try:
            folders = [
                self.working_dir, 
                self.data_dir,
                self.data_dir + "config",
                self.data_dir + "logs",
            ]
            
            for folder in folders:
                if not os.path.exists(folder):
                    os.mkdir(folder)
            
        except Exception as e:
            self.logger.exception(f"LLama failed to make directories: {e}")

    async def question_llama(self, topic, model="mistral"):
        data = {
            "model": "mistral",
            "prompt": topic,
            "stream": False
            }

        url = f"{self.server}/api/generate"

        try:
            async with self.http_session.post(url, json=data) as resp:
                response_data = await resp.json()
                if resp.status != 200:
                    self.logger.error(f"Error occurred in answer_question: {response_data}")
                    return "Error occurred in answer_question"
                response = response_data['response']
                return response

        except Exception as error:
            self.logger.exception("Error occurred in question_llama")
            return "Error occurred in question_llama"
        
    def create_channel_config(self, filepath):
        config_dict = {
            "personality":"average",
            "channel_topic":"casual",
            "chat_enabled":False,
            "chat_history_len":5,
            "react_to_msgs":False,
            "log_images":False,
        }

        with open(filepath,"w") as f:
            json.dump(config_dict,f)
        self.logger.debug("Wrote ChatGPT config variables to file.")

    async def get_channel_config(self, channel_id):
        filepath = f"{self.data_dir}config/{channel_id}.json"
        if not os.path.exists(filepath):
            self.create_channel_config(filepath)
        with open(filepath, "r") as f:
            config_dict = json.loads(f.readline())
        return config_dict

    def edit_channel_config(self, channel_id, key, value):
        config_file = f"{self.data_dir}config/{channel_id}.json"
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        config_data[key] = value
        with open(config_file, "w") as f:
            json.dump(config_data, f)

    def read_db(self,filepath):
        with open(filepath,"r") as fileobj:
            db_content = json.load(fileobj)
        return db_content

    def save_to_db(self,filepath,db_content):
        with open(filepath,"w") as fileobj:
            json.dump(db_content,fileobj,indent=4)

    @commands.command(
        description="Chat", 
        help="Enable or disable bot chat in this channel. Usage !chat (enable|disable)", 
        brief="Enable or disable bot chat"
        )         
    async def llama_chat(self, ctx, message):
        if "enable" in message:
            self.edit_channel_config(ctx.channel.id, "llama_enabled", True)
            await ctx.send("Chat Enabled")
        elif "disable" in message:
            self.edit_channel_config(ctx.channel.id, "llama_enabled", False)
            await ctx.send("Chat Disabled")
        else:
            await ctx.send("Usage: !chat (enable|disable)")

    async def log_chat_and_get_history(self, message, logfile, channel_vars):
        log_line = ''
        if message.attachments and channel_vars.get("log_images", False) and not message.author.bot:
            #log_image MUST BE ADDED TO THE JSON FILES
            for attachment in message.attachments:
                image_description = await self.view_image(attachment.url)
                image_description = image_description.replace("\n"," ")
                log_line += attachment.url + " <image description>" + image_description + "</image description> "
        log_line += message.content
        log_line =  message.author.name + ": " + log_line  +"\n"
        chat_history = ""
        self.logger.debug("Logging: " + log_line, end="")
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(log_line)
        with open(logfile, "r", encoding="utf-8") as f:
            for line in (f.readlines() [-int(channel_vars["chat_history_len"]):]):
                chat_history += line
        return chat_history

    async def chat_response(self, message, channel_vars, chat_history_string):
        async with message.channel.typing(): 
            await asyncio.sleep(1)
            prompt = f"You are a {channel_vars['personality']} chat bot named Sparkytron 3000 created by @phixxy.com. Your personality should be {channel_vars['personality']}. You are currently in a {channel_vars['channel_topic']} chatroom. Only write a response to the last message! DO NOT USE HASHTAGS! The message history is: {chat_history_string}\nSparkytron 3000: "
            response = await self.question_llama(prompt)
            if "Sparkytron 3000:" in response[0:17]:
                response = response.replace("Sparkytron 3000:", "")
            max_len = 1999
            if len(response) > max_len:
                messages=[response[y-max_len:y] for y in range(max_len, len(response)+max_len,max_len)]
            else:
                messages=[response]
            for response_message in messages:
                await message.channel.send(response_message)
        
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Log Chat
        # Todo, make a logging cog to handle this stuff later
        logfile = f"{self.data_dir}logs/{message.channel.id}.log"
        channel_vars = await self.get_channel_config(message.channel.id)
        chat_history_string = await self.log_chat_and_get_history(message, logfile, channel_vars)
        # Chat Response
        try:
            if channel_vars["llama_enabled"] and not message.author.bot or self.bot_id in [x.id for x in message.mentions]:
                if message.content and message.content[0] != "!":
                    await self.chat_response(message, channel_vars, chat_history_string)
                elif not message.content:
                    await self.chat_response(message, channel_vars, chat_history_string)
        except:
            self.edit_channel_config(message.channel.id, "llama_enabled", False)
        
        
async def setup(bot):
    #await bot.add_cog(Llama(bot))
    #Temporarily disable this as it isn't really working properly
    pass