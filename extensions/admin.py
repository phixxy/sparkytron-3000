#Adds administrative commands to the bot
import os
import sys
import logging
import subprocess
from discord.ext import commands

class Admin(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.admin_ids = [242018983241318410]
        self.log_file = "logs/info.log"
        self.logger = logging.getLogger("bot")

    @commands.command(
        description="Kill", 
        help="Kills the bot in event of an emergency. Only special users can do this! Usage: !kill", 
        brief="Kill the bot",
        hidden=True
        )      
    async def kill(self, ctx):
        "Kills the bot"
        if ctx.author.id in self.admin_ids:
            self.logger.info(f"Kill command ran by {ctx.author.id}")
            exit()
        else:
            await ctx.channel.send("You don't have permission to do that.")
            self.logger.info(f"Kill command attempted by {ctx.author.id}")
            
    @commands.command(
        description="Reset", 
        help="Resets the bot in event of an emergency. Only special users can do this! Usage: !reset", 
        brief="Reset the bot",
        hidden=True
        )  
    async def reset(self, ctx):
        if ctx.author.id in self.admin_ids:
            self.logger.info(f"Reset command ran by {ctx.author.id}")
            python = sys.executable
            os.execl(python, python, *sys.argv)
        else:
            await ctx.channel.send("You don't have permission to do that.")
            self.logger.info(f"Reset command attempted by {ctx.author.id}")

    @commands.command(
        description="Update", 
        help="This will update sparkytron to the most recent version on github. Only privileged users can run this command! Usage: !update", 
        brief="Runs git pull",
        hidden=True
        )           
    async def update(self, ctx):
        if ctx.author.id in self.admin_ids:
            self.logger.info(f"Update command ran by {ctx.author.id}")
            output = subprocess.run(["git","pull"],capture_output=True)
            if output.stderr:
                await ctx.send("Update Attempted")
                await ctx.send(output.stderr.decode('utf-8'))
            else:
                await ctx.send(output.stdout.decode('utf-8'))
        else:
            await ctx.send("You don't have permission to do this.")
            self.logger.info(f"Update command attempted by {ctx.author.id}")

    def is_error(self, log_line):
        if "ERROR" in log_line:
            return True
        else:
            return False

    @commands.command(
        description="Errors", 
        help="This will display the last X errors",
        brief="Displays errors",
        hidden=True
        )           
    async def errors(self, ctx, amount=5):
        if ctx.author.id in self.admin_ids:
            self.logger.info(f"Errors command ran by {ctx.author.id}")
            with open(self.log_file, 'r', encoding="utf-8") as log:
                data = log.readlines()
                log.close()
            errors = []
            for line in data[::-1]:
                if self.is_error(line):
                    errors.append(line)
                    if len(errors) >= amount:
                        break
            await ctx.send("```\n" + "\n".join(errors[::-1]) + "```")
        else:
            await ctx.send("You don't have permission to do this.")
            self.logger.info(f"Update command attempted by {ctx.author.id}")

async def setup(bot):
    await bot.add_cog(Admin(bot))