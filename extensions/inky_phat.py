import socket # used to get local IP
import time
import os
import datetime
import psutil
from PIL import Image, ImageFont, ImageDraw
from discord.ext import commands, tasks
import inky

def is_enabled():
    if os.getenv("inky").lower() == "enabled":
        return True
    else:
        return False

class InkyScreen(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.enabled = is_enabled()
        self.old_message = None
        self.display = self.setup()
        self.start_time = time.time()
        self.admin_ids = [242018983241318410]
        self.font_size = 18
        self.message_loop.start()
        
    def setup(self):
        if self.enabled:
            display = inky.auto()
            display.set_border(inky.YELLOW)
            return display
        else:
            return None

    async def write_to_display(self, text: list):
        if text is not self.old_message:
            #try:
            #    image = Image.open("data/inky/bg.png")
            #except:
            #    self.bot.logger.exception("InkyScreen: Failed to load background image.")
            image = Image.new("P", (self.display.WIDTH, self.display.HEIGHT), (self.display.BLACK))
            draw = ImageDraw.Draw(image)
            width = self.display.WIDTH
            height = self.display.HEIGHT
            lines = len(text)
            try:
                height_diff = height/lines
            except:
                self.bot.logger.exception("InkyScreen: Failed to calculate height_diff.")
                self.bot.logger.info(f"InkyScreen: Text: {text}")
                return
            x = 0
            y = 0
            for line in text:
                if y <= width:
                    draw.text((x, y), line, self.display.YELLOW, font=ImageFont.load_default(size=self.font_size))
                    y += height_diff
                else:
                    self.bot.logger.warning("InkyScreen: Text too long to fit on image.")
            image = image.rotate(180)
            self.display.set_image(image)
            self.display.show()
            self.bot.logger.info("InkyScreen: Text successfully written to image.")
            self.old_message = text
        else:
            self.bot.logger.info("InkyScreen: Text is the same as the previous message, not writing to image.")
    
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

    
    async def generate_message(self):
        message_list = []
        try:
            message_list.append(f"IP: {self.get_ip_address()}")
            message_list.append(f"Sys Uptime: {self.get_system_uptime()}")
            message_list.append(f"Bot Uptime: {self.get_bot_uptime()}")
            #message_list.append(f"Last Screen Update: {time.strftime('%H:%M:%S')}")
            #message_list.append(f"Servers: {len(self.bot.guilds)}")
            message_list.append(self.get_cpu_usage())
            message_list.append(self.get_memory_usage())
            message_list.append(self.get_disk_usage())

        except Exception as e:
            self.bot.logger.error(f"Error generating InkyScreen message: {e}")
        return message_list

    
    @commands.command()
    async def inkyscreen_update(self, ctx):
        if ctx.author.id in self.admin_ids:
            message = await self.generate_message()
            await self.write_to_display(message)
            await ctx.send("InkyScreen updated.")
        else:
            await ctx.send("You do not have permission to use this command.")
    
    @tasks.loop(minutes=10)
    async def message_loop(self):
        if self.enabled:
            message = await self.generate_message()
            await self.write_to_display(message)


async def setup(bot):
    await bot.add_cog(InkyScreen(bot))