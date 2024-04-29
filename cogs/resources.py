import time
import psutil
import logging
import datetime
import socket
from discord.ext import commands, tasks

class Resources(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        self.logger = logging.getLogger("bot")

    def get_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    
    def get_bot_uptime(self):
        sparky_uptime = time.time() - self.start_time
        return str(datetime.timedelta(seconds=sparky_uptime))[0:-7]
    
    def get_system_uptime(self):
        system_uptime = time.time() - psutil.boot_time()
        return str(datetime.timedelta(seconds=system_uptime))[0:-7]
    
    def get_memory_usage(self):
        memory_info = psutil.virtual_memory()
        used_memory = memory_info.used
        if used_memory >= 1000000000:
            used_memory = round(used_memory/1000000000,1)
            used_memory = f"{used_memory}GB"
        else:
            used_memory = round(used_memory/1000000)
            used_memory = f"{used_memory}MB"
        total_memory = round(memory_info.total/1000000000,1)
        return f"Memory: {used_memory}/{total_memory}GB"
    
    def get_disk_usage(self):
        disk_info = psutil.disk_usage('/')
        used_disk = disk_info.used
        if used_disk >= 1000000000:
            used_disk = round(used_disk/1000000000,1)
            used_disk = f"{used_disk}GB"
        else:
            used_disk = round(used_disk/1000000)
            used_disk = f"{used_disk}MB"
        total_disk = round(disk_info.total/1000000000,1)
        return f"Disk: {used_disk}/{total_disk}GB"
    
    def get_cpu_usage(self):
        cpu_percent = psutil.cpu_percent()
        return f"CPU: {cpu_percent}%"
    
    @commands.command()
    async def resources(self, ctx):
        message_list = []
        message_list.append(f"IP: {self.get_ip_address()}")
        message_list.append(f"Bot uptime: {self.get_bot_uptime()}")
        message_list.append(f"System uptime: {self.get_system_uptime()}")
        message_list.append(self.get_memory_usage())
        message_list.append(self.get_disk_usage())
        message_list.append(self.get_cpu_usage())
        message = '\n'.join(message_list)
        await ctx.send(message)
    
async def setup(bot):
    await bot.add_cog(Resources(bot))