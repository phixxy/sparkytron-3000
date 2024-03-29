#cog to show message count as a graph
import logging
import os
import time
import matplotlib.pyplot as plt
import discord
from discord.ext import commands


class Highscores(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("bot")

    @commands.command(
        description="Highscores", 
        help="Shows a bar graph of users in this channel and how many messages they have sent.", 
        brief="Display chat highscores",
        aliases=["highscore"]
        ) 
    async def highscores(self, ctx, limit=15):
        filename = str(ctx.channel.id) + ".log"
        with open("data/chatgpt/logs/" + filename, 'r', encoding="utf-8") as logfile:
            data = logfile.readlines()
            logfile.close()
        
        def is_username(user):
            for character in user:
                if character.isupper():
                    return False
                if not (character.isalpha() or character.isdigit() or character == '.' or character == '_'):
                    return False
            return True

        user_message_counts = {}    
        for line in data:
            try:
                user = line[0:line.find(':')]
                if is_username(user):
                    if user not in user_message_counts and user != "" and len(user) <= 32:
                        user_message_counts[user] = 1
                    else:
                        if user != "" and len(user) <= 32:
                            user_message_counts[user] += 1
            except Exception as error:
                self.logger.exception("Error occurred in highscores")
        
        sorted_message_counts = sorted(user_message_counts.items(), key=lambda x:x[1])
        sorted_dict = dict(sorted_message_counts[-limit::])
        keys = list(sorted_dict.keys())
        values = list(sorted_dict.values())
        fig, ax = plt.subplots()
        bar_container = ax.barh(keys, values)
        ax.set_xlabel("Message Count")
        ax.set_ylabel("Username")
        ax.set_title("Messages Sent in " + ctx.channel.name)
        ax.bar_label(bar_container, label_type='center')
        filepath = 'tmp/' + str(time.time_ns()) + '.png'
        plt.savefig(filepath, dpi=1000, bbox_inches="tight")
        with open(filepath, "rb") as fh:
            f = discord.File(fh, filename=str(ctx.channel.id) + '_hiscores.png')
        await ctx.send(file=f)
        

    @commands.command(
        description="Highscores Server", 
        help="Shows a bar graph of users across all servers I am in and how many messages they have sent.", 
        brief="Display chat highscores",
        aliases=["highscore_server"]
        ) 
    async def highscores_server(self, ctx, limit=15):
        
        def is_username(user):
            for character in user:
                if character.isupper():
                    return False
                if not (character.isalpha() or character.isdigit() or character == '.' or character == '_'):
                    return False
            return True

        user_message_counts = {}
        data = []
        for filename in os.listdir("data/chatgpt/logs/"):
            with open("data/chatgpt/logs/" + filename, 'r', encoding="utf-8") as logfile:
                data += logfile.readlines()
                logfile.close()
        user_message_counts = {}    
        for line in data:
            try:
                user = line[0:line.find(':')]
                if is_username(user):
                    if user not in user_message_counts and user != "" and len(user) <= 32:
                        user_message_counts[user] = 1
                    else:
                        if user != "" and len(user) <= 32:
                            user_message_counts[user] += 1
            except Exception as error:
                self.logger.exception("Error occurred in highscores_server")

        sorted_message_counts = sorted(user_message_counts.items(), key=lambda x:x[1])
        sorted_dict = dict(sorted_message_counts[-limit::])
        keys = list(sorted_dict.keys())
        values = list(sorted_dict.values())
        fig, ax = plt.subplots()
        bar_container = ax.barh(keys, values)
        ax.set_xlabel("Message Count")
        ax.set_ylabel("Username")
        ax.set_title("Messages Sent in all channels I can see")
        ax.bar_label(bar_container, label_type='center')
        filepath = 'tmp/' + str(time.time_ns()) + '.png'
        plt.savefig(filepath, dpi=1000, bbox_inches="tight")
        with open(filepath, "rb") as fh:
            f = discord.File(fh, filename=str(ctx.channel.id) + '_hiscores.png')
        await ctx.send(file=f)

async def setup(bot):
    await bot.add_cog(Highscores(bot))