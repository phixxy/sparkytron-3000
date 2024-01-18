#Adds administrative commands to the bot
import os
import sys
import subprocess

from discord.ext import commands

@commands.command(
    description="Kill", 
    help="Kills the bot in event of an emergency. Only special users can do this! Usage: !kill", 
    brief="Kill the bot",
    hidden=True
    )      
async def kill(ctx):
    "Kills the bot"
    if ctx.author.id == 242018983241318410:
        exit()
    else:
        await ctx.channel.send("You don't have permission to do that.")
        
@commands.command(
    description="Reset", 
    help="Resets the bot in event of an emergency. Only special users can do this! Usage: !reset", 
    brief="Reset the bot",
    hidden=True
    )  
async def reset(ctx):
    if ctx.author.id == 242018983241318410:
        python = sys.executable
        os.execl(python, python, *sys.argv)
    else:
        await ctx.channel.send("You don't have permission to do that.")

@commands.command(
    description="Update", 
    help="This will update sparkytron to the most recent version on github. Only privileged users can run this command! Usage: !update", 
    brief="Runs git pull",
    hidden=True
    )           
async def update(ctx):
    if ctx.author.id == 242018983241318410:
        output = subprocess.run(["git","pull"],capture_output=True)
        if output.stderr:
            await ctx.send("Update Attempted")
            await ctx.send(output.stderr.decode('utf-8'))
        else:
            await ctx.send(output.stdout.decode('utf-8'))
    else:
        await ctx.send("You don't have permission to do this.")

async def setup(bot):
    bot.add_command(update)
    bot.add_command(reset)
    bot.add_command(kill)