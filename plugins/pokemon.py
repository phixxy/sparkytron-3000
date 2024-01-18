#plugin file for sparkytron 3000

from discord.ext import commands
import discord
import random
import os
import json
import math
import time
import aiohttp



async def get_json(url):
    http_session = aiohttp.ClientSession()
    async with http_session.get(url) as resp:
            json_data = await resp.json()
    return json_data

@commands.command(
    description="Pokemon", 
    help="Pokemon game", 
    brief="Pokemon Game",
    aliases=['pkmn'],
    hidden=True
    )
async def pokemon(ctx, arg1=None, arg2=None, arg3=None, arg4=None):
    async def starter_picker(id): #id = pokedex number
        url = "https://pokeapi.co/api/v2/pokemon-species/" + str(id)
        json_data = await get_json(url)
        if (json_data["evolves_from_species"] == None) and (not json_data['is_mythical']) and (not json_data['is_legendary']):
            return True
        else:
            return False
    
    async def shiny_roll():
        roll = random.randint(0,2047)
        return not roll
    
    async def save_pokemon(discord_id, pokemon_dict):
        if not os.path.isdir("databases/pokemon/"):
            os.makedirs("databases/pokemon/")

        path = "databases/pokemon/"+str(discord_id)+".json"
        pokemon_dict = json.dumps(pokemon_dict)
        with open(path, 'w') as f:
            f.writelines(pokemon_dict)
        return True
        
    async def load_pokemon(discord_id):
        if not os.path.isdir("databases/pokemon/"):
            os.makedirs("databases/pokemon/")
        if os.path.isfile("databases/pokemon/"+str(discord_id)+".json"):
            with open("databases/pokemon/"+str(discord_id)+".json", 'r') as f:
                json_data = json.loads(f.readline())
            return json_data
        else:
            return False

    async def generate_starter(discord_id):
        random.seed(discord_id)
        json_data = await get_json('https://pokeapi.co/api/v2/pokemon-species/')
        pokemon_count = json_data['count']
        base_pokemon = False
        while not base_pokemon:
            starter_id = random.randint(1,pokemon_count)
            base_pokemon = await starter_picker(starter_id)
        random.seed()
        return starter_id
    
    async def get_pkmn_from_id(id):
        url = 'https://pokeapi.co/api/v2/pokemon/' + str(id)
        json_data = await get_json(url)
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

    if arg1=='start':
        if not os.path.isdir("databases/pokemon/"):
            os.makedirs("databases/pokemon/")
        if not os.path.isfile("databases/pokemon/"+str(ctx.author.id)+'.json'):
            uniq_id = time.time()
            starter_id = await generate_starter(ctx.author.id)
            json_data = await get_pkmn_from_id(starter_id)
            is_shiny = await shiny_roll()
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
            await save_pokemon(ctx.author.id, json_data)
            embed = await make_pmkn_embed(json_data)
            await ctx.channel.send(embed=embed)
            return
        else:
            await ctx.channel.send("You already have a pokemon!")
            return
        
    elif arg1 == 'nick' or arg1 == 'nickname':
        nickname = arg2
        json_data = await load_pokemon(ctx.author.id)
        json_data['nickname'] = nickname
        await save_pokemon(ctx.author.id, json_data)
        message = "You gave " + nickname + ' a new name!'
        await ctx.channel.send(message)
        return
    
    elif arg1 == 'feed':
        json_data = await load_pokemon(ctx.author.id)
        json_data, fed = await give_buddy_food(json_data)
        if fed:
            await save_pokemon(ctx.author.id, json_data)
            if json_data['nickname']:
                message = "You " + arg1 + ' ' + json_data['nickname']
            else:
                message = "You " + arg1 + ' ' + json_data['name']
            await ctx.channel.send(message)
            return
        else:
            if json_data['nickname']:
                message = "Your " + json_data['nickname'] + " isn't hungry!"
            else:
                message = "Your " + json_data['name'] + " isn't hungry!"
            await ctx.channel.send(message)
            return
    
    elif arg1 == 'hug':
        json_data = await load_pokemon(ctx.author.id)
        json_data, hugged = await give_buddy_affection(json_data)
        if hugged:
            await save_pokemon(ctx.author.id, json_data)
            if json_data['nickname']:
                message = "You " + arg1 + ' ' + json_data['nickname']
            else:
                message = "You " + arg1 + ' ' + json_data['name']
            await ctx.channel.send(message)
            return
        else:
            if json_data['nickname']:
                message = "You hugged " + json_data['nickname'] + " but " + json_data['nickname'] + " has been hugged recently."
            else:
                message = "You hugged " + json_data['name'] + " but " + json_data['name'] + " has been hugged recently."
            await ctx.channel.send(message)
            return

    #Default !pokemon behavior (Load and show pokemon embed)
    discord_id = ctx.author.id
    buddy_json = await load_pokemon(discord_id)
    if not buddy_json:
        await ctx.channel.send("You don't have a buddy yet. Type ```!pokemon start``` to start your Pokemon journey!")
    else:
        embed = await make_pmkn_embed(buddy_json)
        message = await ctx.channel.send(embed=embed)
        return

@commands.command(
    description="Pokedex", 
    help="Get information on pokemon", 
    brief="Pokedex",
    aliases=['pdex'],
    hidden=False
    )  
async def pokedex(ctx):
    pokemon = ctx.message.content.split(" ", maxsplit=1)[1]
    try:
        shiny = False
        if 'shiny ' in pokemon:
            shiny = True
            pokemon = pokemon.replace('shiny ', '')
        url = "https://pokeapi.co/api/v2/pokemon/" + pokemon
        dex_url = "https://pokeapi.co/api/v2/pokemon-species/" + pokemon
        #try:
        data = await get_json(url)
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
        dex_data = await get_json(dex_url)
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
    bot.add_command(pokedex)
    bot.add_command(pokemon)
