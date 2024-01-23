#plugin for sparkytron 3000
import json
import os
import time

from discord.ext import commands

async def handle_error(error):
    print(error)
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log_line = current_time + ': ' + str(error) + '\n'
    with open("data/error_log.txt", 'a') as f:
        f.write(log_line)
    return error

def create_channel_config(filepath):
    config_dict = {
        "personality":"average",
        "channel_topic":"casual",
        "chat_enabled":False,
        "commands_enabled":True,
        "chat_history_len":5,
        "look_at_images":False,
        "react_to_msgs":False,
        "ftp_enabled":False
    }

    with open(filepath,"w") as f:
        json.dump(config_dict,f)
    print("Wrote config variables to file.")

async def get_channel_config(channel_id):
    filepath = "channels/config/{0}.json".format(str(channel_id))
    if not os.path.exists(filepath):
        create_channel_config(filepath)
    with open(filepath, "r") as f:
        config_dict = json.loads(f.readline())
    return config_dict

def edit_channel_config(channel_id, key, value):
    config_file = "channels/config/" + str(channel_id) + ".json"
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    config_data[key] = value
    with open(config_file, "w") as f:
        json.dump(config_data, f)

@commands.command(
    description="View Images", 
    help="Enable or disable bot viewing images in this channel. Usage !viewimages (enable|disable)", 
    brief="Enable or disable bot viewing images"
    )         
async def view_images(ctx, message):
    if "enable" in message:
        edit_channel_config(ctx.channel.id, "look_at_images", True)
        await ctx.send("Viewing Enabled")
    elif "disable" in message:
        edit_channel_config(ctx.channel.id, "look_at_images", False)
        await ctx.send("Viewing Disabled")
    else:
        await ctx.send("Usage: !viewimages (enable|disable)")

@commands.command(
    description="Personality", 
    help="Set the personality of the bot. Usage: !personality (personality)", 
    brief="Set the personality"
    )         
async def personality(ctx):
    personality_type = ctx.message.content.split(" ", maxsplit=1)[1]
    edit_channel_config(ctx.channel.id, "personality", personality_type)
    await ctx.send("Personality changed to " + personality_type)

@commands.command(
    description="Commands", 
    help="Enable or disable bot commands in this channel. Usage !enable_commands (enable|disable)", 
    brief="Enable or disable bot commands"
    )         
async def enable_commands(ctx, message):
    if "disable" in message or "false" in message:
        edit_channel_config(ctx.channel.id, "commands_enabled", False)
        await ctx.send("Commands Disabled")
    else:
        edit_channel_config(ctx.channel.id, "commands_enabled", True)
        await ctx.send("Commands Enabled")

@commands.command(
    description="Topic", 
    help="Set the channel topic for the bot. Usage: !topic (topic)", 
    brief="Set channel topic"
    )         
async def topic(ctx, channel_topic):
    edit_channel_config(ctx.channel.id, "channel_topic", channel_topic)
    await ctx.send("Topic changed to " + channel_topic)

@commands.command(
    description="Chat", 
    help="Enable or disable bot chat in this channel. Usage !chat (enable|disable)", 
    brief="Enable or disable bot chat"
    )         
async def chat(ctx, message):
    if "enable" in message:
        edit_channel_config(ctx.channel.id, "chat_enabled", True)
        await ctx.send("Chat Enabled")
    elif "disable" in message:
        edit_channel_config(ctx.channel.id, "chat_enabled", False)
        await ctx.send("Chat Disabled")
    else:
        await ctx.send("Usage: !chat (enable|disable)")
        
@commands.command(
    description="Reactions", 
    help="Enable or disable bot reactions in this channel. Usage !reactions (enable|disable)", 
    brief="Enable or disable bot reactions"
    ) 
async def reactions(ctx, message):
    if "enable" in message:
        edit_channel_config(ctx.channel.id, "react_to_msgs", True)
        await ctx.send("Reactions Enabled")
    elif "disable" in message:
        edit_channel_config(ctx.channel.id, "react_to_msgs", False)
        await ctx.send("Reactions Disabled")
    else:
        await ctx.send("Usage: !reactions (enable|disable)")

@commands.command(
    description="Feature", 
    help="Suggest a feature. Usage: !feature (feature)", 
    brief="Suggest a feature"
    )         
async def feature(ctx):
    try:
        feature = ctx.message.content.split(" ", maxsplit=1)[1]
        with open("features.txt",'a') as f:
            f.writelines('\n' + feature)
        await ctx.send("Added " + feature)
    except Exception as error:
        await handle_error(error)

    with open("features.txt",'r') as f:
        features = f.read()
    await ctx.send(features)

@commands.command(
    description="Errors", 
    help="Shows the last errors that were logged.", 
    brief="Display Errors"
    )       
async def errors(ctx, amount="5"):
    output = ""
    amount = int(amount)
    try:
        with open("data/error_log.txt", 'r') as f:
            for line in (f.readlines() [-amount:]):
                output += line
        await ctx.send(output)
    except Exception as error:
        await handle_error(error)


async def setup(bot):
    bot.add_command(feature)
    bot.add_command(reactions)
    bot.add_command(chat)
    bot.add_command(topic)
    bot.add_command(enable_commands)
    bot.add_command(personality)
    bot.add_command(view_images)
    bot.add_command(errors)