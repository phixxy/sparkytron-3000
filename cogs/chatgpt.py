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
import matplotlib.pyplot as plt

class ChatGPT(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.admin_id = 242018983241318410
        self.API_KEY = os.getenv("openai.api_key")
        self.default_budget = 20
        self.working_dir = "tmp/chatgpt/"
        self.data_dir = "data/chatgpt/"
        self.folder_setup()
        self.remind_me_loop.start()
        self.http_session = self.create_aiohttp_session()
        self.dalle_budget = self.get_budget()
        self.logger = logging.getLogger("bot")
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {os.getenv("openai.api_key")}',
            }

    def create_aiohttp_session(self):
        return aiohttp.ClientSession()

    def folder_setup(self):
        try:
            folders = [
                self.working_dir, 
                self.data_dir,
                self.data_dir + "config",
                self.data_dir + "logs",
                self.data_dir + "dalle",
                self.data_dir + "costs"
            ]
            
            for folder in folders:
                if not os.path.exists(folder):
                    os.mkdir(folder)
            
        except Exception as e:
            self.logger.exception(f"ChatGPT failed to make directories: {e}")

    def text_cost_calc(self, model, input_tokens, output_tokens):
        cost_table = {"gpt-3.5-turbo":{"input_tokens":0.0000005,"output_tokens":0.0000015},
                      "gpt-4-turbo-preview":{"input_tokens":0.00001,"output_tokens":0.00003},
                      "gpt-4-vision-preview":{"input_tokens":0.00001,"output_tokens":0.00003}
        }
        input_cost = cost_table[model]["input_tokens"] * input_tokens
        output_cost = cost_table[model]["output_tokens"] * output_tokens
        cost = input_cost + output_cost
        return cost
    
    def get_budget(self):
        month = time.strftime("%B")
        year = time.strftime("%Y")
        key = f"{month}_{year}"
        budget_file = f"{self.data_dir}budget.json"
        if not os.path.exists(budget_file):
            with open(budget_file, "w") as f:
                json.dump({key:self.default_budget},f)
        with open(budget_file, "r") as f:
            budget_dict = json.loads(f.readline())
        if key not in budget_dict:
            budget_dict[key] = self.default_budget
            with open(budget_file, "w") as f:
                json.dump(budget_dict,f)
            return self.default_budget
        else:
            return budget_dict[key]
        
    def budget_add(self, amount):
        month = time.strftime("%B")
        year = time.strftime("%Y")
        key = f"{month}_{year}"
        budget_file = f"{self.data_dir}budget.json"
        with open(budget_file, "r") as f:
            budget_dict = json.loads(f.readline())
        budget_dict[key] += amount
        with open(budget_file, "w") as f:
            json.dump(budget_dict,f)
            self.dalle_budget += amount

    def add_cost(self, category: str, cost: float):
        day = time.strftime("%d")
        month = time.strftime("%B")
        year = time.strftime("%Y")
        filepath = f"{self.data_dir}costs/{month}_{day}_{year}.json"
        if not os.path.exists(filepath):
            with open(filepath, "w") as f:
                json.dump({},f)
        with open(filepath, "r") as f:
            costs_dict = json.loads(f.readline())
        if category not in costs_dict:
            costs_dict[category] = cost
        else:
            costs_dict[category] += cost
        with open(filepath, "w") as f:
            json.dump(costs_dict,f)

    async def graph_cost(self, graph_title, costs_per_day):
        plt.plot(costs_per_day.values())
        plt.title(f"{graph_title} Costs")
        plt.xlabel("Day")
        plt.ylabel("Cost")
        plt.savefig(f"{self.data_dir}costs/{graph_title}_costs.png")
        plt.close()
        return f"{self.data_dir}costs/{graph_title}_costs.png"
    
    async def graph_category(self, graph_title, cost_per_category):
        bar_container = plt.barh(list(cost_per_category.keys()), cost_per_category.values())
        plt.title(f"{graph_title} Costs")
        plt.xlabel("Category")
        plt.ylabel("Cost")
        plt.bar_label(bar_container)
        plt.savefig(f"{self.data_dir}costs/{graph_title}_categories.png")
        plt.close()
        return f"{self.data_dir}costs/{graph_title}_categories.png"
    
    async def get_monthly_cost(self, month=time.strftime("%B"), year=time.strftime("%Y")):
        total_cost = 0
        for x in range(1,32):
            if x < 10:
                x = f"0{x}"
            filepath = f"{self.data_dir}costs/{month}_{x}_{year}.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    costs_dict = json.loads(f.readline())
                for category, cost in costs_dict.items():
                    total_cost += cost
        return total_cost
    
    async def moderation_check(self, prompt):
        data = {
            "input": prompt
        }

        url = "https://api.openai.com/v1/moderations"


        async with self.http_session.post(url, json=data, headers=self.headers) as resp:
            response_data = await resp.json()
            flagged = response_data['results'][0]['flagged']
            categories = response_data['results'][0]['categories']
            category_scores = response_data['results'][0]['category_scores']
            return (flagged, categories, category_scores)
        
    @commands.command()
    async def budget(self, ctx, command=None, budget=None):
        try:
            if ctx.author.id == self.admin_id:
                if command == "add" and budget!= None:
                    self.budget_add(float(budget))
                    await ctx.send(f"Budget increased by {budget}")
                elif command == "remove" and budget!= None:
                    self.budget_add(-float(budget))
                    await ctx.send(f"Budget decreased by {budget}")
                elif command == "set" and budget!= None:
                    self.budget_add(float(budget) - self.dalle_budget)
                    await ctx.send(f"Budget set to {budget}")
                else:
                    await ctx.send(f"The current budget is {self.dalle_budget}")
            else:
                await ctx.send(f"The current budget is {self.dalle_budget}")
        except Exception as e:
            self.logger.exception(f"Budget command failed: {e}")
            await ctx.send(f"Budget command failed")


    @commands.command(
        name="costs",
        brief="Get the costs for a given month and year.",
        help="Get the costs for a given month and year. If no month or year is given, it will default to the current month and year.",
        aliases=["cost"],
        usage="costs [month] [year]",
    )
    async def costs(self, ctx, month=time.strftime("%B"), year=time.strftime("%Y")):
        total_cost = 0
        cost_per_day = {}
        for x in range(1,32):
            daily_cost = 0
            if x < 10:
                x = f"0{x}"
            filepath = f"{self.data_dir}costs/{month}_{x}_{year}.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    costs_dict = json.loads(f.readline())
                for category, cost in costs_dict.items():
                    total_cost += cost
                    daily_cost += cost
            cost_per_day[x] = daily_cost
        rounded_total = round(total_cost, 2)
        if rounded_total == 0:
            await ctx.send(f"No data for {month} {year}")
        else:
            graph_title = f"{month} {year}"
            await ctx.send(f"Total cost for {month} {year}: ${rounded_total}", file=discord.File(await self.graph_cost(graph_title, cost_per_day)))

    @commands.command(
        name="category_costs",
        brief="Get the costs per category for a given month and year.",
        help="Get the costs per category for a given month and year. If no month or year is given, it will default to the current month and year.",
        aliases=["category_cost"],
        usage="category_costs [month] [year] [day]",
    )
    async def category_costs(self, ctx, month=time.strftime("%B"), year=time.strftime("%Y"), day=None):
        total_cost = 0
        cost_per_category = {}
        if day == None:
            day_range = range(1,32)
        else:
            day_range = [int(day)]
        for x in day_range:
            daily_cost = 0
            if x < 10:
                x = f"0{x}"
            filepath = f"{self.data_dir}costs/{month}_{x}_{year}.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    costs_dict = json.loads(f.readline())
                for category, cost in costs_dict.items():
                    if category not in cost_per_category:
                        cost_per_category[category] = cost
                    else:
                        cost_per_category[category] += cost
                    total_cost += cost
        graph_title = f"{month} {year}"
        rounded_total = round(total_cost, 2)
        if rounded_total == 0:
            await ctx.send(f"No data for {month} {year}")
        else:
            await ctx.send(f"Total cost for {month} {year}: ${rounded_total}", file=discord.File(await self.graph_category(graph_title, cost_per_category)))

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

    async def remind(self,reminder_dict): #THIS IS THE FUNCTION TO AUTOMATICALLY FULFILL THE RESPONSE WHEN CALLED BY THE REMIND ME LOOP
        #this is what the reminder_dict looks like: data[target_time] = {"user_id":user_id,"response":response}
        user = self.bot.get_user(reminder_dict["user_id"])
        return await user.send(reminder_dict["response"])

    async def answer_question(self, topic, model="gpt-3.5-turbo"):
        data = {
            "model": model,
            "messages": [{"role": "user", "content": topic}]
        }

        url = "https://api.openai.com/v1/chat/completions"

        try:
            async with self.http_session.post(url, json=data, headers=self.headers) as resp:
                response_data = await resp.json()
                if resp.status != 200:
                    self.logger.error(f"Error occurred in answer_question: {response_data}")
                    return "Error occurred in answer_question"
                response = response_data['choices'][0]['message']['content']
                input_tokens = response_data['usage']['prompt_tokens']
                output_tokens = response_data['usage']['completion_tokens']
                cost = self.text_cost_calc(model, input_tokens, output_tokens)
                self.add_cost(model, cost)
                return response

        except Exception as error:
            self.logger.exception("Error occurred in answer_question")
            return "Error occurred in answer_question"
        
        
    @commands.command(
        description="Personality",
        help="Set the personality of the bot. Usage: !personality (personality)",
        brief="Set the personality"
    )
    async def personality(self, ctx, *personality_type):
        if personality_type:
            personality_type = ' '.join(personality_type)
            self.edit_channel_config(ctx.channel.id, "personality", personality_type)
            await ctx.send(f"Personality changed to {personality_type}")
        else:
            channel_config = await self.get_channel_config(ctx.channel.id)
            current_personality = channel_config["personality"]
            await ctx.send(f"Current personality is {current_personality}")


    @commands.command(
        description="Topic",
        help="Set the channel topic for the bot. Usage: !topic (topic)",
        brief="Set channel topic"
    )
    async def topic(self, ctx, *channel_topic):
        if channel_topic:
            channel_topic = ' '.join(channel_topic)
            self.edit_channel_config(ctx.channel.id, "channel_topic", channel_topic)
            await ctx.send(f"Topic changed to {channel_topic}")
        else:
            channel_config = await self.get_channel_config(ctx.channel.id)
            current_topic = channel_config["channel_topic"]
            await ctx.send(f"Current topic is {current_topic}")


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
        description="Log Images", 
        help="Enable or disable logging images in this channel. Usage !log_images (enable|disable)", 
        brief="Enable or disable bot logging images"
        )         
    async def log_images(self, ctx, message):
        if "enable" in message:
            self.edit_channel_config(ctx.channel.id, "log_images", True)
            await ctx.send("Image Viewing Enabled")
        elif "disable" in message:
            self.edit_channel_config(ctx.channel.id, "log_images", False)
            await ctx.send("Image Viewing Disabled")
        else:
            await ctx.send("Usage: !log_images (enable|disable)")
            
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
        await ctx.send("One moment, let me think...")
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
        await ctx.send("One moment, let me think...")
        question = ctx.message.content.split(" ", maxsplit=1)[1]
        answer = await self.answer_question(question, "gpt-4-turbo-preview")
        chunks = [answer[i:i+1999] for i in range(0, len(answer), 1999)]
        for chunk in chunks:
            await ctx.send(chunk)
    
    async def dalle_api_call(self, prompt: str, model: str="dall-e-2", quality: str="standard", size: str="1024x1024") -> tuple:
        if self.dalle_budget <= await self.get_monthly_cost():
            self.logger.info("DALL-E API call failed due to budget")
            return (1337, "DALL-E API call failed due to budget. Consider using !donate to fund the bot.")
        data = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n":1,
        }
        url = "https://api.openai.com/v1/images/generations"
        async with self.http_session.post(url, json=data, headers=self.headers) as resp:
            response_data = await resp.json()
            if resp.status == 200:
                response = response_data['data'][0]['url']
            else:
                response = response_data["error"]["message"]
                self.logger.info(f"Error occurred in dalle: {resp.status} | {response}")
            return (resp.status, response)
    
    async def download_image(self, url, destination) -> int:
        async with self.http_session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(destination, mode='wb')
                await f.write(await resp.read())
                await f.close()
            return resp.status
        
    async def send_moderation_message(self, command, user_id, username, prompt, categories, category_scores):
        categories = [k for k, v in categories.items() if v]
        category_scores = {k: v for k, v in category_scores.items() if v > 0.5}
        embed = discord.Embed(title="Moderation", description=f"Command: {command}\nUsername: {username}\nUser ID: {user_id}\nPrompt: {prompt}\nCategories: {categories}\nCategory Scores: {category_scores}", color=0x00ff00)
        embed.set_footer(text="Moderation")
        user = self.bot.get_user(self.admin_id)
        await user.send(embed=embed)

    async def generate_dalle_image(self, ctx, model, quality="standard", size="1024x1024") -> None:
        prompt = ctx.message.content.split(" ", maxsplit=1)[1]
        await ctx.send(f"Please be patient this may take some time! Generating: {prompt}.")
        flagged, categories, category_scores = await self.moderation_check(prompt)
        if flagged:
            self.logger.info(f"Prompt {prompt} was flagged for inappropriate content.")
            await ctx.send(f"This prompt {prompt} was flagged for inappropriate content. This has been reported.")
            await self.send_moderation_message("dalle", ctx.author.id, ctx.author.name, prompt, categories, category_scores)
            return
        resp_status, resp = await self.dalle_api_call(prompt, model=model, quality=quality, size=size)
        if resp_status != 200:
            await ctx.send(f"Error generating image: {resp_status}: {resp}")
            return
        my_filename = str(time.time_ns()) + ".png"
        image_filepath = f"{self.data_dir}dalle/{my_filename}"
        await self.download_image(resp, image_filepath)
        with open(image_filepath, "rb") as fh:
            f = discord.File(fh, filename=image_filepath)
        prompt = prompt.replace('\n',' ')
        log_data = f'Author: {ctx.author.name}, Prompt: {prompt}, Filename: {my_filename}\n'
        with open(f"{self.data_dir}logs/dalle3.log", 'a') as log_filepath:
            log_filepath.writelines(log_data)
        await ctx.send(f'Generated by: {ctx.author.name}\nPrompt: {prompt}', file=f)

    @commands.command(
        description="Big Spenders",
        help="Generate a list of the biggest spenders. Usage: !bigspenders",
        brief="Generate list of big spenders"
        )
    async def bigspenders(self, ctx):
        filenames = os.listdir(self.data_dir + "logs/")
        user_cost_dict = {}
        for filename in filenames:
            if ".log" in filename:
                with open(f"{self.data_dir}logs/{filename}", 'r', encoding="utf-8") as f:
                    for line in f:
                        try:
                            if "!dalle3hd" in line:
                                cost = 0.08
                                username = line[0:line.index(':')]
                                if " " in username:
                                    break
                                if username not in user_cost_dict:
                                    user_cost_dict[username] = 0
                                user_cost_dict[username] += cost
                            elif "!dalle2" in line:
                                cost = 0.02
                                username = line[0:line.index(':')]
                                if " " in username:
                                    break
                                if username not in user_cost_dict:
                                    user_cost_dict[username] = 0
                                user_cost_dict[username] += cost
                            if "!dalle" in line or "!dalle3" in line:
                                cost = 0.04
                                username = line[0:line.index(':')]
                                if " " in username:
                                    break
                                if username not in user_cost_dict:
                                    user_cost_dict[username] = 0
                                user_cost_dict[username] += cost
                            else:
                                pass
                        except:
                            pass
        message = "Big Spenders:\n"
        sorted_dictionary = sorted(user_cost_dict.items(), key=lambda x: x[1], reverse=True)
        for user in sorted_dictionary:
            message += f"{user[0]}: ${user[1]:.2f}\n"
        await ctx.send(message)


    @commands.command(
        description="Dalle 2", 
        help="Generate an image with Dalle 2 Usage: !dalle2 (prompt)", 
        brief="Generate Image"
        )         
    async def dalle2(self, ctx):
        self.add_cost("dalle2", 0.02)
        await self.generate_dalle_image(ctx, model="dall-e-2")


    @commands.command(
        description="Dalle 3", 
        help="Generate an image with Dalle 3 Usage: !dalle3 (prompt)", 
        brief="Generate Image",
        aliases = ['dalle']
        )           
    async def dalle3(self, ctx):
        self.add_cost("dalle3", 0.04)
        await self.generate_dalle_image(ctx, model="dall-e-3")


    @commands.command(
        description="Dalle 3 HD", 
        help="Generate an HD image with Dalle 3 Usage: !dalle3 (prompt)", 
        brief="Generate HD Image",
        )           
    async def dalle3hd(self, ctx):
        self.add_cost("dalle3hd", 0.08)
        await self.generate_dalle_image(ctx, model="dall-e-3", quality="hd", size="1792x1024")

    @commands.command(
        description="Looker", 
        help="Ask GPT4 a question about an image. Usage: !looker (link) (question)", 
        brief="Get an answer"
        )         
    async def looker(self, ctx):
        if len(ctx.message.attachments) > 0:
           image_link = ctx.message.attachments[0].url
           question = ctx.message.content
        else:
            image_link = ctx.message.content.split(" ", maxsplit=2)[1]
            question = ctx.message.content.split(" ", maxsplit=2)[2]

        data = {
            "model": "gpt-4-vision-preview",
            "messages": [{"role": "user", "content": [{"type": "text", "text": question},{"type": "image_url","image_url": {"url": image_link}}]}],
            "max_tokens": 500
        }

        url = "https://api.openai.com/v1/chat/completions"

        try:
            async with self.http_session.post(url, json=data, headers=self.headers) as resp:
                response_data = await resp.json()
                self.logger.debug(response_data)
                answer = response_data['choices'][0]['message']['content']
            

        except Exception as error:
            self.logger.exception("error occurred in looker")
        
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
        reminder_data = self.read_db(reminders_path)
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
        reminder_data[target_time] = {"user_id":user_id,"response":response}

        self.logger.info(f"Reminding user {ctx.author.id} in {duration_s} seconds || Target time (ns): {target_time}")
        self.save_to_db(reminders_path,reminder_data)

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
                    self.logger.info(f"Reminder sent successfully to {reminder_dict['user_id']}")
                    trash.append(remind_time) #NEED TO POP OR THEY WILL GET REMINDED AD INFINITUM

        for key in trash:
            if data.pop(key):
                self.logger.debug("Fulfilled reminders successfully purged")

        self.save_to_db(reminders_path,data)
    
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
                
                data = { 
                    "model": "gpt-3.5-turbo", 
                    "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": message}]
                }

                url = "https://api.openai.com/v1/chat/completions"
                
                try:
                    async with self.http_session.post(url, json=data, headers=self.headers) as resp:
                        response_data = await resp.json()
                        reaction = response_data['choices'][0]['message']['content'].strip()
                    if is_emoji(reaction):
                        await ctx.add_reaction(reaction)
                    else:
                        await ctx.add_reaction("😓")
                except Exception as error:
                    self.logger.exception("Some error happened while trying to react to a message")

    async def view_image(self, image_link):
        data = {
            "model": "gpt-4-vision-preview",
            "messages": [{"role": "user", "content": [{"type": "text", "text": "Describe this"},{"type": "image_url","image_url": {"url": image_link}}]}],
            "max_tokens": 500
        }

        url = "https://api.openai.com/v1/chat/completions"

        try:
            async with self.http_session.post(url, json=data, headers=self.headers) as resp:
                response_data = await resp.json()
                self.logger.debug(response_data)
                answer = response_data['choices'][0]['message']['content']
            
        except Exception as error:
            self.logger.exception("error occurred in view_image")
        
        return answer

    async def chat_response(self, message, channel_vars, chat_history_string):
        async with message.channel.typing(): 
            await asyncio.sleep(1)
            prompt = f"You are a {channel_vars['personality']} chat bot named Sparkytron 3000 created by @phixxy.com. Your personality should be {channel_vars['personality']}. You are currently in a {channel_vars['channel_topic']} chatroom. The message history is: {chat_history_string}\nSparkytron 3000: "
            response = await self.answer_question(prompt)
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