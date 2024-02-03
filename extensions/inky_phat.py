import socket # used to get local IP
import time
import datetime
import psutil
from PIL import Image, ImageFont, ImageDraw
from discord.ext import commands, tasks
import inky

class InkyScreen(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.enabled = False
        self.old_message = None
        self.display = self.setup()
        self.start_time = time.time()
        
    def setup(self):
        display = inky.auto()
        display.set_border(inky.BLACK)
        return display

    def write_to_image(self, text: list):
        if text is not self.old_message:
            image = Image.new("P", (self.display.WIDTH, self.display.HEIGHT))
            draw = ImageDraw.Draw(image)
            height = self.display.HEIGHT
            lines = len(text)
            height_diff = height/lines
            x, y = 0
            for line in text:
                if x <= height:
                    draw.text((x, y), line, self.display.YELLOW)
                    x += height_diff
                else:
                    self.bot.logger.warning("InkyScreen: Text too long to fit on image.")
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
    
    def get_uptime(self):
        sparky_uptime = time.time() - self.start_time
        return str(datetime.timedelta(seconds=sparky_uptime))
    
    @tasks.loop(minutes=10)
    async def update_screen(self):
        message_list = []
        if self.enabled:
            message_list.append(f"IP: {self.get_ip_address()}")
            message_list.append(f"Time: {time.strftime('%H:%M:%S')}") 
            message_list.append(f"Uptime: {self.get_uptime()}")
            message_list.append(f"Servers: {len(self.bot.guilds)}")
            cpu_percent = psutil.cpu_percent()
            memory_info = psutil.virtual_memory()
            message_list.append(f"CPU: {cpu_percent}%")  
            message_list.append(f"Memory: {memory_info.used}/{memory_info.total}")

            



        
async def setup(bot):
    await bot.add_cog(InkyScreen(bot))