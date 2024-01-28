#plugin file for sparkytron 3000
from discord.ext import commands
import discord
import random
import os
import json
import math
import time

class PokemonGame(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.working_dir = "tmp/pokemon/"
        self.data_dir = "data/pokemon/"
        self.folder_setup()

    def folder_setup(self):
        try:
            if not os.path.exists(self.working_dir):
                os.mkdir(self.working_dir)
            if not os.path.exists(self.data_dir):
                os.mkdir(self.data_dir)
        except:
            self.bot.logger.exception("PokemonGame failed to make directories")

    async def get_json(self, url):
        async with self.bot.http_session.get(url) as resp:
                json_data = await resp.json()
        return json_data

    @commands.command(
        description="Pokemon", 
        help="Pokemon game", 
        brief="Pokemon Game",
        aliases=['pkmn'],
        hidden=True
        )
    async def pokemon(self, ctx, *args):
        async def starter_picker(id): #id = pokedex number
            url = "https://pokeapi.co/api/v2/pokemon-species/" + str(id)
            json_data = await self.get_json(url)
            if (json_data["evolves_from_species"] == None) and (not json_data['is_mythical']) and (not json_data['is_legendary']):
                return True
            else:
                return False
        
        async def shiny_roll():
            roll = random.randint(0,2047)
            return not roll
        
        async def save_pokemon(discord_id, pokemon_dict):
            path = self.data_dir+str(discord_id)+".json"
            pokemon_dict = json.dumps(pokemon_dict)
            with open(path, 'w') as f:
                f.writelines(pokemon_dict)
            return True
            
        async def load_pokemon(discord_id):
            if os.path.isfile(self.data_dir+str(discord_id)+".json"):
                with open(self.data_dir+str(discord_id)+".json", 'r') as f:
                    json_data = json.loads(f.readline())
                return json_data
            else:
                return False

        async def generate_starter(discord_id):
            random.seed(discord_id)
            json_data = await self.get_json('https://pokeapi.co/api/v2/pokemon-species/')
            pokemon_count = json_data['count']
            base_pokemon = False
            while not base_pokemon:
                starter_id = random.randint(1,pokemon_count)
                base_pokemon = await starter_picker(starter_id)
            random.seed()
            return starter_id
        
        async def get_pkmn_from_id(id):
            url = 'https://pokeapi.co/api/v2/pokemon/' + str(id)
            json_data = await self.get_json(url)
            return json_data
        
        async def give_buddy_food(pkmn_data):
            try:
                last_food = pkmn_data['last_food']
            except:
                last_food = 0
            this_food = time.time()
            if (this_food - last_food) >= 1800:
                pkmn_data['last_food'] = this_food
                level = await calc_pkmn_buddy_level(pkmn_data)
                pkmn_data['buddy_xp'] += (4*level)
                return pkmn_data, True
            else:
                return pkmn_data, False

        async def give_buddy_affection(pkmn_data):
            try:
                last_hug = pkmn_data['last_hug']
            except:
                last_hug = 0
            this_hug = time.time()
            if (this_hug - last_hug) >= 600:
                pkmn_data['last_hug'] = this_hug
                level = await calc_pkmn_buddy_level(pkmn_data)
                pkmn_data['buddy_xp'] += (3*level)
                return pkmn_data, True
            else:
                return pkmn_data, False
        
        async def calc_pkmn_buddy_level(pkmn_json): #this uses the 'fast' xp rate
            buddy_xp = pkmn_json['buddy_xp']
            return min(math.floor(((5*buddy_xp)/4)**(1/3)),100)
        
        async def make_pmkn_embed(pkmn_dict):
            if pkmn_dict['nickname']:
                title = pkmn_dict['nickname'] + ' (' + pkmn_dict['name'].capitalize() + ')'
            else:
                title = pkmn_dict['name'].capitalize()
            embed=discord.Embed(title=title)
            if pkmn_dict['shiny']:
                embed.set_image(url=pkmn_dict['sprites']['front_shiny'])
            else:
                embed.set_image(url=pkmn_dict['sprites']['front_default'])
            nature = pkmn_dict['nature']
            buddy_level = await calc_pkmn_buddy_level(pkmn_dict)
            buddy_xp = pkmn_dict['buddy_xp']
            types = []
            for key in pkmn_dict['types']:
                types.append(key['type']['name'].capitalize())
            type_str = ', '.join(types)
            embed.add_field(name="Nature", value=nature.capitalize(), inline=False)
            embed.add_field(name="Buddy Level", value=buddy_level , inline=True)
            embed.add_field(name="Buddy XP", value=buddy_xp, inline=True)
            embed.add_field(name="Types", value=type_str, inline=False)
            return embed
        try:
            if args[0]=='start':
                if not os.path.isfile(self.data_dir+str(ctx.author.id)+'.json'):
                    uniq_id = time.time()
                    starter_id = await generate_starter(ctx.author.id)
                    json_data = await get_pkmn_from_id(starter_id)
                    is_shiny = await shiny_roll()
                    nature = random.randint(0,19)
                    nature_data = await self.get_json('https://pokeapi.co/api/v2/nature/')
                    nature = nature_data['results'][nature]['name']
                    json_data['shiny'] = is_shiny
                    json_data['nickname'] = None
                    json_data['unique_id'] = uniq_id
                    json_data['nature'] = nature
                    json_data['buddy_level'] = 1
                    json_data['buddy_xp'] = 0
                    json_data['last_food'] = 0
                    json_data['last_hug'] = 0
                    await save_pokemon(ctx.author.id, json_data)
                    embed = await make_pmkn_embed(json_data)
                    await ctx.channel.send(embed=embed)
                    return
                else:
                    await ctx.channel.send("You already have a pokemon!")
                    return
                
            elif args[0] == 'nick' or args[0] == 'nickname':
                nickname = args[1]
                json_data = await load_pokemon(ctx.author.id)
                json_data['nickname'] = nickname
                await save_pokemon(ctx.author.id, json_data)
                message = "You gave " + nickname + ' a new name!'
                await ctx.channel.send(message)
                return
            
            elif args[0] == 'feed':
                json_data = await load_pokemon(ctx.author.id)
                json_data, fed = await give_buddy_food(json_data)
                if fed:
                    await save_pokemon(ctx.author.id, json_data)
                    if json_data['nickname']:
                        message = "You " + args[0] + ' ' + json_data['nickname']
                    else:
                        message = "You " + args[0] + ' ' + json_data['name']
                    await ctx.channel.send(message)
                    return
                else:
                    if json_data['nickname']:
                        message = "Your " + json_data['nickname'] + " isn't hungry!"
                    else:
                        message = "Your " + json_data['name'] + " isn't hungry!"
                    await ctx.channel.send(message)
                    return
            
            elif args[0] == 'hug':
                json_data = await load_pokemon(ctx.author.id)
                json_data, hugged = await give_buddy_affection(json_data)
                if hugged:
                    await save_pokemon(ctx.author.id, json_data)
                    if json_data['nickname']:
                        message = "You " + args[0] + ' ' + json_data['nickname']
                    else:
                        message = "You " + args[0] + ' ' + json_data['name']
                    await ctx.channel.send(message)
                    return
                else:
                    if json_data['nickname']:
                        message = "You hugged " + json_data['nickname'] + " but " + json_data['nickname'] + " has been hugged recently."
                    else:
                        message = "You hugged " + json_data['name'] + " but " + json_data['name'] + " has been hugged recently."
                    await ctx.channel.send(message)
                    return
        except:
            #Default !pokemon behavior (Load and show pokemon embed)
            discord_id = ctx.author.id
            buddy_json = await load_pokemon(discord_id)
            if not buddy_json:
                await ctx.channel.send("You don't have a buddy yet. Type ```!pokemon start``` to start your Pokemon journey!")
            else:
                embed = await make_pmkn_embed(buddy_json)
                message = await ctx.channel.send(embed=embed)
                return
        
    async def pkmn_msg(self, discord_id):
        path = self.data_dir+str(discord_id)+'.json'
        if os.path.isfile(path):
            with open(path, 'r') as f:
                json_data = json.loads(f.readline())
                json_data['buddy_xp'] += random.randint(1,5)
                json_data = json.dumps(json_data)
            with open(path, 'w') as f:
                f.writelines(json_data)
        
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.pkmn_msg(message.author.id)


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
            #try:
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
            message = "No data for " + str(pokemon)
            await ctx.channel.send(message)

async def setup(bot):
    try:
        await bot.add_cog(PokemonGame(bot))
        bot.logger.info("Successfully added PokemonGame Cog")
    except:
        bot.logger.info("Failed to load PokemonGame Cog")
