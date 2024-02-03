#plugin file for sparkytron 3000
from discord.ext import commands
import discord
import random
import os
import json
import math
import time

async def get_json(self, url):
    async with self.bot.http_session.get(url) as resp:
            json_data = await resp.json()
    return json_data

#@commands.cooldown(1, 60, commands.BucketType.user) Cooldowns....

class Pokemon:
    async def __init__(self, id: int, generate: bool = True) -> None:
        if generate: # Should I even do it this way?
            self.json_data = await self.get_pkmn_from_id(id)

    async def get_pkmn_from_id(id):
        url = 'https://pokeapi.co/api/v2/pokemon/' + str(id)
        json_data = await get_json(url)
        return json_data

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

    async def starter_picker(self, id): #id = pokedex number
        url = "https://pokeapi.co/api/v2/pokemon-species/" + str(id)
        json_data = await get_json(url)
        if (json_data["evolves_from_species"] == None) and (not json_data['is_mythical']) and (not json_data['is_legendary']):
            return True
        else:
            return False
    
    async def shiny_roll(self):
        roll = random.randint(0,2047)
        return not roll
    
    async def save_pokemon(self, discord_id, pokemon_dict):
        path = self.data_dir+str(discord_id)+".json"
        pokemon_dict = json.dumps(pokemon_dict)
        with open(path, 'w') as f:
            f.writelines(pokemon_dict)
        return True
        
    async def load_pokemon(self, discord_id):
        if os.path.isfile(self.data_dir+str(discord_id)+".json"):
            with open(self.data_dir+str(discord_id)+".json", 'r') as f:
                json_data = json.loads(f.readline())
            return json_data
        else:
            return False

    async def generate_starter(self, discord_id):
        random.seed(discord_id)
        json_data = await get_json('https://pokeapi.co/api/v2/pokemon-species/')
        pokemon_count = json_data['count']
        base_pokemon = False
        while not base_pokemon:
            starter_id = random.randint(1,pokemon_count)
            base_pokemon = await self.starter_picker(starter_id)
        random.seed()
        return starter_id
    
    async def get_pkmn_from_id(self, id):
        url = 'https://pokeapi.co/api/v2/pokemon/' + str(id)
        json_data = await get_json(url)
        return json_data
    
    async def give_buddy_food(self, pkmn_data):
        try:
            last_food = pkmn_data['last_food']
        except:
            last_food = 0
        this_food = time.time()
        if (this_food - last_food) >= 1800:
            pkmn_data['last_food'] = this_food
            level = await self.calc_pkmn_buddy_level(pkmn_data)
            pkmn_data['buddy_xp'] += (4*level)
            return pkmn_data, True
        else:
            return pkmn_data, False

    async def give_buddy_affection(self, pkmn_data):
        try:
            last_hug = pkmn_data['last_hug']
        except:
            last_hug = 0
        this_hug = time.time()
        if (this_hug - last_hug) >= 600:
            pkmn_data['last_hug'] = this_hug
            level = await self.calc_pkmn_buddy_level(pkmn_data)
            pkmn_data['buddy_xp'] += (3*level)
            return pkmn_data, True
        else:
            return pkmn_data, False
    
    async def calc_pkmn_buddy_level(self, pkmn_json): #this uses the 'fast' xp rate
        buddy_xp = pkmn_json['buddy_xp']
        return min(math.floor(((5*buddy_xp)/4)**(1/3)),100)
    
    async def make_pmkn_embed(self, pkmn_dict):
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
        buddy_level = await self.calc_pkmn_buddy_level(pkmn_dict)
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

    @commands.command()
    async def pkmn_start(self, ctx):
        if not os.path.isfile(self.data_dir+str(ctx.author.id)+'.json'):
            uniq_id = time.time()
            starter_id = await self.generate_starter(ctx.author.id)
            json_data = await self.get_pkmn_from_id(starter_id)
            is_shiny = await self.shiny_roll()
            nature = random.randint(0,19)
            nature_data = await get_json('https://pokeapi.co/api/v2/nature/')
            nature = nature_data['results'][nature]['name']
            json_data['shiny'] = is_shiny
            json_data['nickname'] = None
            json_data['unique_id'] = uniq_id
            json_data['nature'] = nature
            json_data['buddy_level'] = 1
            json_data['buddy_xp'] = 0
            json_data['last_food'] = 0
            json_data['last_hug'] = 0
            await self.save_pokemon(ctx.author.id, json_data)
            embed = await self.make_pmkn_embed(json_data)
            await ctx.channel.send(embed=embed)
            return
        else:
            await ctx.channel.send("You already have a pokemon!")
            return

                
    @commands.command()
    async def pkmn_nick(self, ctx, nickname):
        json_data = await self.load_pokemon(ctx.author.id)
        json_data['nickname'] = nickname 
        await self.save_pokemon(ctx.author.id, json_data)
        message = "You gave " + nickname + " a new name!"
        await ctx.channel.send(message)

            
    @commands.command()
    @commands.cooldown(1, 3600, commands.BucketType.user)  
    async def pkmn_feed(self, ctx):
        discord_id = ctx.author.id
        json_data = await self.load_pokemon(discord_id)
        json_data, fed = await self.give_buddy_food(json_data)
        if fed:
            await self.save_pokemon(ctx.author.id, json_data)
            if json_data['nickname']:
                message = "You Feed " + json_data['nickname']
            else:
                message = "You Feed " + json_data['name']
            await ctx.channel.send(message)
            return

            
    @commands.command()
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def pkmn_hug(self, ctx):
        discord_id = ctx.author.id
        json_data = await self.load_pokemon(discord_id)
        json_data, hugged = await self.give_buddy_affection(json_data)
        if hugged:
            await self.save_pokemon(discord_id, json_data)
            if json_data['nickname']:
                message = "You " + "hugged" + ' ' + json_data['nickname'] 
            else:
                message = "You " + "hugged" + ' ' + json_data['name']
            await ctx.channel.send(message)


    @commands.command()
    async def pokemon(self, ctx):
        discord_id = ctx.author.id
        buddy_json = await self.load_pokemon(discord_id)
        if not buddy_json:
            await ctx.channel.send("You don't have a buddy yet. Type ```!pokemon start``` to start your Pokemon journey!")
        else:
            embed = await self.make_pmkn_embed(buddy_json)
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

async def setup(bot):
    try:
        await bot.add_cog(PokemonGame(bot))
        bot.logger.info("Successfully added PokemonGame Cog")
    except:
        bot.logger.exception("Failed to load PokemonGame Cog")
