#sparkytron3000 plugin
from discord.ext import commands

@commands.command(
    description="RSGP", 
    help="Uses probably outdated information to calculate how much rsgp is worth in usd. Usage: !rsgp (amount)", 
    brief="Runescape gold to usd"
    )       
async def rsgp(ctx, amount):
    output = ""
    cost_per_bil = 25.50 #1b rsgp to usd
    cost_per_bil_os = 210
    gold_per_bond = 70000000
    gold_per_bond_os = 7000000
    cost_per_bond = 8 #dollars usd
    bondcost = (int(amount)/gold_per_bond) * cost_per_bond
    rwtcost = (int(amount) * cost_per_bil / 1000000000)
    dollar_gp = (int(amount)*1000000000)/cost_per_bil
    osbondcost = (int(amount)/gold_per_bond_os) * cost_per_bond
    osrwtcost = (int(amount) * cost_per_bil_os / 1000000000)
    osdollar_gp = (int(amount)*1000000000)/cost_per_bil_os
    output += str(amount) + ' rs3 gp would cost: $' + str(round(rwtcost,2)) + " (RWT)\n"
    output += str(amount) + ' osrs gp would cost: $' + str(round(osrwtcost,2)) + " (RWT)\n"
    output += str(amount) + ' rs3 gp would cost: $' + str(round(bondcost,2)) + " (Bonds)\n"
    output += str(amount) + ' osrs gp would cost: $' + str(round(osbondcost,2)) + " (Bonds)\n"
    output += str(amount) + ' dollars spent on rs3 gp would be: ' + str(round(dollar_gp,2)) + " (RS3 GP)\n"
    output += str(amount) + ' dollars spent on osrs gp would be: ' + str(round(osdollar_gp,2)) + " (OSRS GP)\n"
    await ctx.send(output)

async def setup(bot):
    bot.add_command(rsgp)