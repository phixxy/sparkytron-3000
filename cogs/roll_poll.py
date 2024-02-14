import random
import discord
from discord.ext import commands

@commands.command(
    description="Poll", 
    help='Create a poll with up to 9 options. Usage: !poll "Put question here" "option 1" "option 2"', 
    brief="Enable or disable bot reactions"
    ) 
async def poll(ctx, question, *options: str):
    if len(options) > 9:
        await ctx.send("Error: You cannot have more than 9 options")
        return

    embed = discord.Embed(title=question, colour=discord.Colour(0x283593))
    for i, option in enumerate(options):
        embed.add_field(name=f"Option {i+1}", value=option, inline=False)

    message = await ctx.send(embed=embed)
    numbers = {0: "\u0030\ufe0f\u20e3", 1: "\u0031\ufe0f\u20e3", 2: "\u0032\ufe0f\u20e3", 3: "\u0033\ufe0f\u20e3", 4: "\u0034\ufe0f\u20e3", 5: "\u0035\ufe0f\u20e3", 6: "\u0036\ufe0f\u20e3", 7: "\u0037\ufe0f\u20e3", 8: "\u0038\ufe0f\u20e3", 9: "\u0039\ufe0f\u20e3"}
    for i in range(len(options)):
        await message.add_reaction(numbers.get(i+1))
        
@commands.command(
    description="Roll", 
    help="Rolls dice mostly for Dungeons and Dragons type games. Usage: !roll 3d6+2", 
    brief="Simulate rolling dice"
    ) 
async def roll(ctx, dice_string):
    dice_parts = dice_string.split('d')
    num_dice = int(dice_parts[0])
    if '+' in dice_parts[1]:
        die_parts = dice_parts[1].split('+')
        die_size = int(die_parts[0])
        modifier = int(die_parts[1])
    elif '-' in dice_parts[1]:
        die_parts = dice_parts[1].split('-')
        die_size = int(die_parts[0])
        modifier = -int(die_parts[1])
    else:
        die_size = int(dice_parts[1])
        modifier = 0

    rolls = [random.randint(1, die_size) for i in range(num_dice)]
    dice_str = ' + '.join([str(roll) for roll in rolls])
    total = sum(rolls) + modifier

    await ctx.send(f'{dice_str} + {modifier} = {total}' if modifier != 0 else f'{dice_str} = {total}')

async def setup(bot):
    bot.add_command(roll)
    bot.add_command(poll)