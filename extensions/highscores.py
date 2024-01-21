#plugin to show message count as a graph
import os
import time
import matplotlib.pyplot as plt

import discord
from discord.ext import commands

async def handle_error(error):
    print(error)
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log_line = current_time + ': ' + str(error) + '\n'
    with open("databases/error_log.txt", 'a') as f:
        f.write(log_line)
    return error

@commands.command(
    description="Highscores", 
    help="Shows a bar graph of users in this channel and how many messages they have sent.", 
    brief="Display chat highscores",
    aliases=["highscore"]
    ) 
async def highscores(ctx, limit=0):
    filename = str(ctx.channel.id) + ".log"
    with open("channels/logs/" + filename, 'r', encoding="utf-8") as logfile:
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
                    user_message_counts[user] += 1
        except Exception as error:
            await handle_error(error)
    
    def remove_dict_keys_if_less_than_x(dictionary,x):
        for key in dictionary:
            if dictionary[key] <= x:
                dictionary.pop(key)
                return remove_dict_keys_if_less_than_x(dictionary,x)
        return dictionary
    
    print(user_message_counts)   
    remove_dict_keys_if_less_than_x(user_message_counts,limit) 
    keys = list(user_message_counts.keys())
    values = list(user_message_counts.values())
    fig, ax = plt.subplots()
    bar_container = ax.barh(keys, values)
    ax.set_xlabel("Message Count")
    ax.set_ylabel("Username")
    ax.set_title("Messages Sent in " + ctx.channel.name)
    ax.bar_label(bar_container, label_type='center')
    plt.savefig(str(ctx.channel.id) + '_hiscores.png', dpi=1000, bbox_inches="tight")
    with open(str(ctx.channel.id) + '_hiscores.png', "rb") as fh:
        f = discord.File(fh, filename=str(ctx.channel.id) + '_hiscores.png')
    await ctx.send(file=f)
    

@commands.command(
    description="Highscores Server", 
    help="Shows a bar graph of users across all servers I am in and how many messages they have sent.", 
    brief="Display chat highscores",
    aliases=["highscore_server"]
    ) 
async def highscores_server(ctx, limit=0):

    def remove_dict_keys_if_less_than_x(dictionary,x):
        for key in dictionary:
            if dictionary[key] <= x:
                dictionary.pop(key)
                return remove_dict_keys_if_less_than_x(dictionary,x)
        return dictionary
    
    def is_username(user):
        for character in user:
            if character.isupper():
                return False
            if not (character.isalpha() or character.isdigit() or character == '.' or character == '_'):
                return False
        return True

    user_message_counts = {}
    data = []
    for filename in os.listdir("channels/logs/"):
        with open("channels/logs/" + filename, 'r', encoding="utf-8") as logfile:
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
                    user_message_counts[user] += 1
        except Exception as error:
            await handle_error(error)

    print(user_message_counts)
    print("printed")
    user_message_counts = remove_dict_keys_if_less_than_x(user_message_counts,limit)
    keys = user_message_counts.keys()
    print(keys)
    values = user_message_counts.values()
    print(values)
    fig, ax = plt.subplots()
    bar_container = ax.barh(keys, values)
    ax.set_xlabel("Message Count")
    ax.set_ylabel("Username")
    ax.set_title("Messages Sent in all channels I can see")
    ax.bar_label(bar_container, label_type='center')
    plt.savefig(str(ctx.channel.id) + '_hiscores.png', dpi=1000, bbox_inches="tight")
    with open(str(ctx.channel.id) + '_hiscores.png', "rb") as fh:
        f = discord.File(fh, filename=str(ctx.channel.id) + '_hiscores.png')
    await ctx.send(file=f)

async def setup(bot):
    bot.add_command(highscores)
    bot.add_command(highscores_server)