from discord.ext import commands
import discord

class Pokedex(commands.Cog):

    def __init__(self, bot) -> None:
        self.bot = bot

    async def get_json(self, url):
        async with self.bot.http_session.get(url) as resp:
                json_data = await resp.json()
        return json_data
    
    @commands.command(
        description="Pokedex", 
        help="Get information on pokemon", 
        brief="Pokedex",
        aliases=['pdex'],
        hidden=False
        )  
    async def pokedex(self, ctx):
        pokemon = ctx.message.content.split(" ", maxsplit=1)[1]
        try:
            shiny = False
            if 'shiny ' in pokemon:
                shiny = True
                pokemon = pokemon.replace('shiny ', '')
            url = "https://pokeapi.co/api/v2/pokemon/" + pokemon
            dex_url = "https://pokeapi.co/api/v2/pokemon-species/" + pokemon
            data = await self.get_json(url)
            name = data['name']
            height_str = str(int(data['height'])/10) + 'm'
            weight_str = str(int(data['weight'])/10) + 'kg'
            type1 = data['types'][0]['type']['name']
            try:
                type2 = data['types'][1]['type']['name']
                type_str = type1.capitalize() + ', ' + type2.capitalize()
            except:
                type2 = "None"
                type_str = type1.capitalize()
            sprite = data["sprites"]["front_default"]
            if shiny:
                sprite = data["sprites"]["front_shiny"]
            dex_data = await self.get_json(dex_url)
            generation = dex_data['generation']['name'].upper().replace("GENERATION","Generation")
            for entry in dex_data['flavor_text_entries']:
                if entry['language']['name'] == 'en':
                    dex_desc = entry['flavor_text'].replace("\u000c", '\n')
                    dex_desc_game = entry['version']['name'].capitalize()
                    break
            for entry in dex_data['genera']:
                if entry['language']['name'] == 'en':
                    genus = entry['genus']
                    break
            footer = generation + ' | Pokédex entry from Pokémon ' + dex_desc_game
            dex_num = dex_data['pokedex_numbers'][0]['entry_number']
            embed=discord.Embed(title=name.capitalize())
            embed.set_image(url=sprite)
            embed.add_field(name="Number", value=dex_num, inline=False)
            embed.add_field(name=genus, value=dex_desc, inline=False)
            embed.add_field(name="Weight", value=weight_str , inline=True)
            embed.add_field(name="Height", value=height_str, inline=True)
            embed.add_field(name="Types", value=type_str, inline=True)
            embed.set_footer(text=footer)
            await ctx.send(embed=embed)
        except:
            self.bot.logger.exception("Something went wrong in pokedex")
            message = "No data for " + str(pokemon)
            await ctx.channel.send(message)

async def setup(bot):
    try:
        await bot.add_cog(Pokedex(bot))
        bot.logger.info("Successfully added Pokedex Cog")
    except:
        bot.logger.info("Failed to load Pokedex Cog")