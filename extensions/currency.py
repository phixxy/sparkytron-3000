#plugin for sparkytron3000
import time
import random
import json
import math

from discord.ext import commands

@commands.command(
    description="Currency", 
    help="Server currency. You can run !currency claim to get started!", #This needs an overhaul
    brief="Server currency tools"
    )        
async def currency(ctx, arg1=None, arg2=None, arg3=None, arg4=None): # just use *args
    
    def read_db(filepath):
        with open(filepath,"r") as fileobj:
            db_content = json.load(fileobj)
        return db_content

    def save_to_db(filepath,db_content):
        with open(filepath,"w") as fileobj:
            json.dump(db_content,fileobj,indent=4)

    def add_currency(filepath,amount):
        player_db = read_db(filepath)
        player_db["currency"] += amount
        save_to_db(filepath,player_db)
        return player_db
        
    def calc_level_from_xp(xp):
        level = min(100,math.floor(0.262615*xp**0.3220627))
        return level
    
    def add_xp(filepath,player_db,time_spent):
        activity = player_db["status"]["current_activity"]
        starting_xp = player_db["skills"][activity]["xp"]
        starting_level = player_db["skills"][activity]["level"]
        

        if activity == "mining":
            equipment_level = player_db["equipment"]["pickaxe"]["level"]
            xp_gained = (time_spent) * equipment_level # SKILL LEVEL of XP / SEC
        player_db["skills"][activity]["xp"] += xp_gained
        new_xp = starting_xp + xp_gained
        new_level = calc_level_from_xp(new_xp) #calculate with curve here
        player_db["skills"][activity]["level"] = new_level
        levels_gained = new_level - starting_level

        summary = "" #summary should include xp gained, levels gained (only if any were gained), current level (or new level)
        summary += "You gained {} {} xp!".format(xp_gained, activity)
        if levels_gained > 0: #if levels gained > 0, then include levels gained in summary
            summary += "\nYou gained {} {} level(s)! You are now level {}.".format(levels_gained, activity, new_level)

        save_to_db(filepath, player_db)
        return player_db,summary

    def add_resources(filepath,player_db,time_spent):

        mining_resources = {
            "sapphire": {
                "value": 100,
                "amount": 0
            },
            "emerald": {
                "value": 250,
                "amount": 0
            },
            "ruby": {
                "value": 1000,
                "amount": 0
            },
            "diamond": {
                "value": 3000,
                "amount": 0
            }
        }

        if player_db["status"]["current_activity"] == "mining":
            pick_power = player_db["equipment"]["pickaxe"]["power"]
            pick_level = player_db["equipment"]["pickaxe"]["level"]
            mining_level = player_db["skills"]["mining"]["level"]
            numerator = pick_power + pick_level + mining_level
            denominator = 1000
            items_gained = []
            time_summary = time.strftime("%H:%M:%S", time.gmtime(time_spent))

            for second in range(0,time_spent):
                roll = random.randint(0,denominator)
                if roll <= numerator: #get a resource
                    roll2 = random.randint(0,100)
                    if roll2 <= 50:
                        mining_resources["sapphire"]["amount"] += 1
                    elif roll2 <=80:
                        mining_resources["emerald"]["amount"] += 1
                    elif roll2 <= 95:
                        mining_resources["ruby"]["amount"] += 1
                    else:
                        mining_resources["diamond"]["amount"] += 1
            for item in mining_resources:
                mined_amount = mining_resources[item]["amount"]
                if item in player_db["items"]:
                    player_db["items"][item]["amount"] += mined_amount
                    items_gained.append(item.title())
                    items_gained.append(mined_amount)
                else:
                    player_db["items"][item] = mining_resources[item]
                    items_gained.append(item.title())
                    items_gained.append(mined_amount)

            save_to_db(filepath, player_db)

            summary = "You spent {} mining. You mined {} x{}, {} x{}, {} x{}, and {} x{}.".format(time_summary, *items_gained)

            return player_db,summary
            
    async def transfer_currency(filepath, player_db, player_id, amount):
        try:
            amount = int(amount)
            player2_filepath = "data/currency/players/" + str(player_id) + ".json"
            player2_db = read_db(player2_filepath)
            if player_db["currency"] >= amount:
                add_currency(filepath, -amount)
                add_currency(player2_filepath,amount)
                await ctx.send("Sent " + str(amount) + " sparks to " + str(player_id))
        except FileNotFoundError:
            await ctx.send("They don't seem to be playing the game.")
        
    
    async def show_levels(player_db):
        output = ''
        for skill in player_db["skills"]:
            output += skill + ': ' + str(player_db["skills"][skill]["level"]) + '\n'
        await ctx.send(output)
        
    async def show_currency(player_db):
        output = 'Sparks: ' + str(player_db["currency"])
        await ctx.send(output)
        
    async def show_items(player_db):
        output = ''
        for item in player_db["items"]:
            output += item + ': ' + str(player_db["items"][item]["amount"]) + '\n'
        await ctx.send(output)
            

    async def stop_activity(filepath,player_db):
        if player_db["status"]["current_activity"] == "idle":
            await ctx.send("You are currently idle. There is no activity to stop.")
        else:
            time_spent = int(time.time() - player_db["status"]["start_time"]) #integer in seconds
            player_db, xp_summary = add_xp(filepath,player_db,time_spent)
            player_db, resources_summary = add_resources(filepath,player_db,time_spent)
            await ctx.send(xp_summary)
            await ctx.send(resources_summary)
            player_db["status"]["current_activity"] = "idle"
            save_to_db(filepath,player_db)
        
    async def claim(filepath, player_db):
        if time.time() - player_db["status"]["last_claimed"] >= 86400:
            player_db = add_currency(filepath, 100)
            player_db["status"]["last_claimed"] = time.time()
            save_to_db(filepath,player_db)
            await ctx.send("You claimed 100 sparks!")
        else:
            await ctx.send("Sorry, you already claimed your sparks today.")
        
    async def mine(filepath, player_db):
        if player_db["status"]["current_activity"] == "idle":
            player_db["status"]["current_activity"] = "mining"
            player_db["status"]["start_time"] = time.time()
            save_to_db(filepath, player_db)
            await ctx.send("You start mining.")
        elif player_db["status"]["current_activity"] == "mining":
            await ctx.send("You are already mining!")
        else:
            await ctx.send("You must stop " + player_db["status"]["current_activity"] + " before you start mining!")
            
    async def gamble(filepath, player_db):
        pass
    
    working_dir = "data/currency/"
    players_dir = "players/"
    sender_id = str(ctx.author.id)
    default_db = read_db("{0}{1}default.json".format(working_dir, players_dir))
    filepath = '{0}{1}{2}.json'.format(working_dir, players_dir, sender_id)

    try:
        player_db = read_db(filepath)
    except FileNotFoundError:
        save_to_db(filepath,default_db)
        player_db = read_db(filepath)
        
    if arg1 == "claim":
        await claim(filepath, player_db)
        player_db = read_db(filepath)
    elif arg1 == "stop":
        await stop_activity(filepath, player_db)
        player_db = read_db(filepath)
    elif arg1 == "mine":
        await mine(filepath, player_db)
        player_db = read_db(filepath)
    elif arg1 == "levels":
        await show_levels(player_db)
    elif arg1 == "items":
        await show_items(player_db)
    elif (arg1 == "send" or arg1 == "give") and arg2 and arg3:
        await transfer_currency(filepath, player_db, arg2, arg3) 
        player_db = read_db(filepath)
    else:
        await show_currency(player_db)

async def setup(bot):
    bot.add_command(currency)