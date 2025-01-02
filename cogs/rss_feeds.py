from discord.ext import commands, tasks
from cogs.base_cog.bot_base_cog import BotBaseCog
import feedparser

class RSSCog(BotBaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        self.setup(__class__.__name__)
        self.rss_url = 'https://secure.runescape.com/m=adventurers-log/rssfeed?searchName=Frozener'
        self.last_item = None
        self.check_rss.start()

    @tasks.loop(minutes=1)
    async def check_rss(self):
        feed = feedparser.parse(self.rss_url)
        latest_item = feed.entries[0] if feed.entries else None
        
        if latest_item and latest_item.title != self.last_item:
            self.last_item = latest_item.title
            channel = self.bot.get_channel(895388842834673696)
            await channel.send(f"New RSS Item: {latest_item.title} - {latest_item.link}")
    
    @check_rss.before_loop
    async def before_check_rss(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(RSSCog(bot))