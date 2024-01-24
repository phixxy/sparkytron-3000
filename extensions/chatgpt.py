#sparkytron 3000 plugin
import os
import time
import json
from discord.ext import commands, tasks

class ChatGPT(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.API_KEY = os.getenv("openai.api_key")
        self.working_dir = "tmp/chatgpt/"
        self.data_dir = "data/chatgpt/"
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
        except:
            print("AsyncOpenAI failed to make directories")

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
        print("Wrote ChatGPT config variables to file.")

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
            async with self.bot.http_session.post(url, headers=headers, json=data) as resp:
                response_data = await resp.json()
                response = response_data['choices'][0]['message']['content']
                return response

        except Exception as error:
            return await self.handle_error(error)
        
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
            async with self.bot.http_session.post(url, headers=headers, json=data) as resp:
                response_data = await resp.json()
                print(response_data)
                answer = response_data['choices'][0]['message']['content']
            

        except Exception as error:
            return await self.handle_error(error)
        
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
        #DEBUG
        print("Called command successfully")
        
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

        print(f"Reminding user {ctx.author.id} in {duration_s} seconds || Target time (ns): {target_time}")
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
                    print(f"Reminder sent successfully to {reminder_dict['user_id']}")
                    trash.append(remind_time) #NEED TO POP OR THEY WILL GET REMINDED AD INFINITUM

        for key in trash:
            if data.pop(key):
                print("Fulfilled reminders successfully purged")

        self.save_to_db(reminders_path,data)
        
        
async def setup(bot):
    await bot.add_cog(ChatGPT(bot))