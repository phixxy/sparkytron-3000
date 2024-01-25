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

'''
#stable diffusion command!!!
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
        await ctx.send("Usage: !viewimages (enable|disable)")'''


'''
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
        await ctx.send("Commands Enabled")'''


'''
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
    await ctx.send(features)'''

'''@commands.command(
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
        await handle_error(error)'''

