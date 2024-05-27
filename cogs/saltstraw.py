from discord.ext import commands
from cogs.base_cog.bot_base_cog import BotBaseCog
import aiohttp
from bs4 import BeautifulSoup as bs

#ice cream role, only mention those
#get container of new flavors, not old
#save container as raw data to compare new scrapes for updates, must be able to contain variable number of flavors
#separate into variables the following info: series name (flavorsTitle), flavor name (flavorItemTitle / packModalTitle), flavor desc (packModalBody)
#parse all flavors, flag anything different from saved data. replace data with new flavor list in case classics have been updated
#div id="west_coast" is the all-encompassing container for west coast flavors
#packModalContentPadding
#post link

class SaltStraw(BotBaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        self.setup(__class__.__name__)
        self.url = "https://saltandstraw.com/pages/flavors"

    @commands.command()
    async def icecream(self, ctx):
        message = await self.parse()
        await ctx.send(message)
        self.logger.info(f"SaltStraw command called by {ctx.author.name}")

    async def parse(self):
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(self.url) as resp:
                html = await resp.text()
                page = bs(html, "html.parser")
                flavor_data = page.find("div", {"id": "west_coast"}) #extracts only west coast flavors

                flavor_dict = {}
                parent_sets = flavor_data.find_all("div", {"class": "packModalContentPadding"}) #starting at this tag, closest findable line
                for item in parent_sets:
                    child_set = item.find_all("div", limit=3) #limit=3 skips everything past each description, i.e. ingredients/allergens
                    flavor_dict[child_set[0].string] = child_set[1].string #grabbing only the title and description
                message = ""
                for item in flavor_dict:
                    print(f"\n{item}:\n{flavor_dict[item]}\n\n")
                    message += f"\n{item}:\n"
                return message
                
async def setup(bot):
    await bot.add_cog(SaltStraw(bot))