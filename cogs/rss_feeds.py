from discord.ext import commands, tasks
from cogs.base_cog.bot_base_cog import BotBaseCog
import feedparser

class RSSCog(BotBaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        self.setup(__class__.__name__)
        self.rss_base_url = 'https://secure.runescape.com/m=adventurers-log/rssfeed?searchName='
        self.usernames = ['Deadifyed', 'Frozener']
        self.last_items = {key: None for key in self.usernames}
        self.check_rss.start()

    @tasks.loop(minutes=1)
    async def check_rss(self):
        for name in self.usernames:
            rss_url = self.rss_base_url + name
            feed = feedparser.parse(rss_url)
            latest_item = feed.entries[0] if feed.entries else None
            
            if latest_item and latest_item.title != self.last_items[name]:
                self.last_items[name] = latest_item.title
                channel = self.bot.get_channel(895388842834673696)
                await channel.send(f"{name}: {latest_item.description}")
    
    @check_rss.before_loop
    async def before_check_rss(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(RSSCog(bot))