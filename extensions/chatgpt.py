#sparkytron 3000 plugin
import os
import time
import json
import random
import asyncio
import discord
from discord.ext import commands, tasks

class ChatGPT(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.API_KEY = os.getenv("openai.api_key")
        self.working_dir = "tmp/chatgpt/"
        self.data_dir = "data/chatgpt/"
        self.premium_role = 1200943915579228170
        self.folder_setup()
        self.remind_me_loop.start()


    def folder_setup(self):
        try:
            if not os.path.exists(self.working_dir):
                os.mkdir(self.working_dir)
            if not os.path.exists(self.data_dir):
                os.mkdir(self.data_dir)
            if not os.path.exists(self.data_dir + "config"):
                os.mkdir(self.data_dir + "config")
            if not os.path.exists(self.data_dir + "logs"):
                os.mkdir(self.data_dir + "logs")
        except:
            self.bot.logger.exception("ChatGPT failed to make directories")

    def create_channel_config(self, filepath):
        config_dict = {
            "personality":"average",
            "channel_topic":"casual",
            "chat_enabled":False,
            "chat_history_len":5,
            "react_to_msgs":False,
        }

        with open(filepath,"w") as f:
            json.dump(config_dict,f)
        self.bot.logger.debug("Wrote ChatGPT config variables to file.")

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

    async def remind(self,reminder_dict): #THIS IS THE FUNCTION TO AUTOMATICALLY FULFILL THE RESPONSE WHEN CALLED BY THE REMIND ME LOOP
        #this is what the reminder_dict looks like: data[target_time] = {"user_id":user_id,"response":response}
        user = self.bot.get_user(reminder_dict["user_id"])
        return await user.send(reminder_dict["response"])

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
            self.bot.logger.exception("Error occurred in answer_question")
            return "Error occurred in answer_question"
        
    async def get_dalle(self, prompt, model="dall-e-2"):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {os.getenv("openai.api_key")}',
        }
        data = {
            "model": model,
            "prompt": prompt,
            "size": "1024x1024",
            "quality": "standard",
            "n":1,
        }
        url = "https://api.openai.com/v1/images/generations"

        try:
            async with self.bot.http_session.post(url, headers=headers, json=data) as resp:
                response_data = await resp.json()
                response = response_data[0]['url']
                return response

        except Exception as error:
            self.bot.logger.exception("Error occurred in dalle")
            return "Error occurred in dalle"
        
    @commands.command(
        description="Personality", 
        help="Set the personality of the bot. Usage: !personality (personality)", 
        brief="Set the personality"
        )         
    async def personality(self, ctx):
        personality_type = ctx.message.content.split(" ", maxsplit=1)[1]
        self.edit_channel_config(ctx.channel.id, "personality", personality_type)
        await ctx.send("Personality changed to " + personality_type)

    @commands.command(
        description="Topic", 
        help="Set the channel topic for the bot. Usage: !topic (topic)", 
        brief="Set channel topic"
        )         
    async def topic(self, ctx, channel_topic):
        self.edit_channel_config(ctx.channel.id, "channel_topic", channel_topic)
        await ctx.send("Topic changed to " + channel_topic)

    @commands.command(
        description="Chat", 
        help="Enable or disable bot chat in this channel. Usage !chat (enable|disable)", 
        brief="Enable or disable bot chat"
        )         
    async def chat(self, ctx, message):
        if "enable" in message:
            self.edit_channel_config(ctx.channel.id, "chat_enabled", True)
            await ctx.send("Chat Enabled")
        elif "disable" in message:
            self.edit_channel_config(ctx.channel.id, "chat_enabled", False)
            await ctx.send("Chat Disabled")
        else:
            await ctx.send("Usage: !chat (enable|disable)")
            
    @commands.command(
        description="Reactions", 
        help="Enable or disable bot reactions in this channel. Usage !reactions (enable|disable)", 
        brief="Enable or disable bot reactions"
        ) 
    async def reactions(self, ctx, message):
        if "enable" in message:
            self.edit_channel_config(ctx.channel.id, "react_to_msgs", True)
            await ctx.send("Reactions Enabled")
        elif "disable" in message:
            self.edit_channel_config(ctx.channel.id, "react_to_msgs", False)
            await ctx.send("Reactions Disabled")
        else:
            await ctx.send("Usage: !reactions (enable|disable)")

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
        if ctx.author.get_role(self.premium_role):
            question = ctx.message.content.split(" ", maxsplit=1)[1]
            answer = await self.answer_question(question, "gpt-4")
            chunks = [answer[i:i+1999] for i in range(0, len(answer), 1999)]
            for chunk in chunks:
                await ctx.send(chunk)
        else:
            await ctx.send("Sorry you must be a premium member to use this command. (!donate)")

    @commands.command(
        description="Dalle 2", 
        help="Generate an image with Dalle 2 Usage: !dalle2 (prompt)", 
        brief="Generate Image",
        aliases = ['dalle']
        )         
    async def dalle2(self, ctx):
        if ctx.author.get_role(self.premium_role):
            prompt = ctx.message.content.split(" ", maxsplit=1)[1]
            img_url = await self.get_dalle(prompt)
            await ctx.send("Generated by: {ctx.author.name}\nPrompt: {prompt}\n{img_url}")
        else:
            await ctx.send("Sorry you must be a premium member to use this command. (!donate)")

    @commands.command(
        description="Dalle 3", 
        help="Generate an image with Dalle 3 Usage: !dalle3 (prompt)", 
        brief="Generate Image"
        )           
    async def dalle3(self, ctx):
        if ctx.author.get_role(self.premium_role):
            prompt = ctx.message.content.split(" ", maxsplit=1)[1]
            img_url = await self.get_dalle(prompt, "dall-e-3")
            await ctx.send("Generated by: {ctx.author.name}\nPrompt: {prompt}\n{img_url}")
        else:
            await ctx.send("Sorry you must be a premium member to use this command. (!donate)")
            
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
            async with self.bot.http_session.post(url, headers=headers, json=data) as resp:
                response_data = await resp.json()
                self.bot.logger.debug(response_data)
                answer = response_data['choices'][0]['message']['content']
            

        except Exception as error:
            self.bot.logger.exception("error occurred in looker")
        
        chunks = [answer[i:i+1999] for i in range(0, len(answer), 1999)]
        for chunk in chunks:
            await ctx.send(chunk)

    @commands.command(
        description="Remind Me",
        help="Send a request in natural language to ask Sparky to remind you of a task or event by direct message in a specified amount of time. Minimum 1 minute.",
        brief="Get a reminder",
        aliases=["remindme","remind_me","remind"]
    )
    async def save_reminder(self,ctx):
        #SETUP
        reminders_path = self.data_dir + "reminders.txt"
        if not os.path.exists(reminders_path):
            with open(reminders_path,"w") as file_obj:
                file_obj.write("{}")
        prompt = ctx.message.content.split(" ", maxsplit=1)[1]
        data = self.read_db(reminders_path)
        current_time = int(time.time_ns())
        user_id = ctx.author.id
        
        #PARSE PROMPT
        duration_s = await self.answer_question(f"You are an automated bot whose only function is to convert a natural language number into an integer. You must determine a number representing after how long, in seconds, the user wishes you to remind them of a task based on the information provided. Please respond using only an integer of the equivalent or approximate time in seconds. You must not use any words in your response other than a single integer representing that time in seconds. You are incapable of using any English words at all. If you are unable to determine a time from the prompt given, return only the integer 0. The prompt is as follows: {prompt}")
        response = await self.answer_question(f"You are a reminder bot whose purpose is to help users by reminding them of tasks or events. A user by the name of {ctx.author.name} has asked you to remind them about something after a certain amount of time has passed. That time has now passed. Their original request was as follows: {prompt}")
        if duration_s == "0":
            await ctx.reply("Sorry! I'm not sure exactly when you need me to remind you based on your wording. Could you phrase the request a bit differently?",mention_author=True)
            return
        else:
            await ctx.reply("Sure thing! I'll remind you when the time comes.", mention_author=False)
        #MATHS
        duration_ns = int(duration_s) * 1000000000
        target_time = current_time + int(duration_ns)

        #CREATE FILEDUMP
        data[target_time] = {"user_id":user_id,"response":response}

        self.bot.logger.info(f"Reminding user {ctx.author.id} in {duration_s} seconds || Target time (ns): {target_time}")
        self.save_to_db(reminders_path,data)

    @tasks.loop(seconds=60) # THIS ONE NEEDS TO POP AND THEN CALL THE REMIND FUNC
    async def remind_me_loop(self):
        reminders_path = self.data_dir + "reminders.txt"
        current_time = int(time.time_ns())
        data = self.read_db(reminders_path)
        trash = []

        #CHECK IF ANY NEED TO BE FULFILLED
        for remind_time in data.keys():
            if current_time >= int(remind_time):
                reminder_dict = data[remind_time]
                sent = await self.remind(reminder_dict) #THIS SENDS THE REMINDER DICT TO REMIND FUNC
                if sent:
                    self.bot.logger.info(f"Reminder sent successfully to {reminder_dict['user_id']}")
                    trash.append(remind_time) #NEED TO POP OR THEY WILL GET REMINDED AD INFINITUM

        for key in trash:
            if data.pop(key):
                self.bot.logger.debug("Fulfilled reminders successfully purged")

        self.save_to_db(reminders_path,data)
    
    async def log_chat_and_get_history(self, ctx, logfile, channel_vars):
        #todo: ctx is actually a message, make this obv
        log_line = ''           
        log_line += ctx.content
        log_line =  ctx.author.name + ": " + log_line  +"\n"
        chat_history = ""
        self.bot.logger.debug("Logging: " + log_line, end="")
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(log_line)
        with open(logfile, "r", encoding="utf-8") as f:
            for line in (f.readlines() [-int(channel_vars["chat_history_len"]):]):
                chat_history += line
        return chat_history
    
    async def react_to_msg(self, ctx, react):
        #todo ctx is actually a message, make this obv
        def is_emoji(string):
            if len(string) == 1:
                # Range of Unicode codepoints for emojis
                if 0x1F300 <= ord(string) <= 0x1F6FF:
                    return True
            return False
        
        if react:
            if not random.randint(0,10) and ctx.author.id != 1097302679836971038:
                #todo above line is do not react to self, make this work programatically
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
                    async with self.bot.http_session.post(url, headers=headers, json=data) as resp:
                        response_data = await resp.json()
                        reaction = response_data['choices'][0]['message']['content'].strip()
                    if is_emoji(reaction):
                        await ctx.add_reaction(reaction)
                    else:
                        await ctx.add_reaction("😓")
                except Exception as error:
                    self.bot.logger.exception("Some error happened while trying to react to a message")

    async def chat_response(self, ctx, channel_vars, chat_history_string): 
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
                async with self.bot.http_session.post(url, headers=headers, json=data) as resp:
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
                self.bot.logger.exception("Problem with chat_response in chatgpt")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if not random.randint(0,9):
            message = reaction.message
            emoji = reaction.emoji
            await message.add_reaction(emoji)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Log Chat
        # Todo, make a logging cog to handle this stuff later
        logfile = f"{self.data_dir}logs/{message.channel.id}.log"
        channel_vars = await self.get_channel_config(message.channel.id)
        chat_history_string = await self.log_chat_and_get_history(message, logfile, channel_vars)
        # Emoji Reaction
        await self.react_to_msg(message, channel_vars["react_to_msgs"])
        # Chat Response
        if channel_vars["chat_enabled"] and not message.author.bot:
            if message.content and message.content[0] != "!":
                await self.chat_response(message, channel_vars, chat_history_string)
            elif not message.content:
                await self.chat_response(message, channel_vars, chat_history_string)
        
        
async def setup(bot):
    await bot.add_cog(ChatGPT(bot))