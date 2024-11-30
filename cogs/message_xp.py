from discord.ext import commands
import discord
import json
import os
from cogs.base_cog.bot_base_cog import BotBaseCog

class MessageXP(BotBaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        self.setup(__class__.__name__)

    @commands.command()
    async def stats(self, ctx):
        author_id = str(ctx.author.id)
        try:
            xp_data = read_xp_file(self)
            if author_id in xp_data:
                level = get_level_from_xp(xp_data[author_id])
                await ctx.send(f"You are level {level} with {xp_data[author_id]} XP")
            else:
                await ctx.send("You have 0 XP")
        except:
            await ctx.send("Error getting XP")

    @commands.command()
    async def show_json(self, ctx):
        with open(os.path.join(self.data_dir, "xp.json"), "r") as xp_file:
            xp_data = json.load(xp_file)
        await ctx.send(xp_data)
            

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            author_id = str(message.author.id)
            if message.author.bot:
                return
            else:
                xp_data = read_xp_file(self)
                if author_id in xp_data:
                    xp_data[author_id] += 1
                else:
                    xp_data[author_id] = 1

                with open(os.path.join(self.data_dir, "xp.json"), "w") as xp_file:
                    json.dump(xp_data, xp_file)
        except Exception as e:
            self.logger.error(f"Error adding XP: {e}")

def read_xp_file(self):
    try:
        with open(os.path.join(self.data_dir, "xp.json"), "r") as xp_file:
            xp_data = json.load(xp_file)
        return xp_data
    except Exception as e:
        self.logger.error(f"No XP file found. Returning empty json object: {e}")
        return {}

def get_level_from_xp(xp):
    xp_dict = {
        1: 0,
        2: 83,
        3: 174,
        4: 276,
        5: 388,
        6: 512,
        7: 650,
        8: 801,
        9: 801,
        10: 1_154,
        11: 1_358,
        12: 1_584,
        13: 1_833,
        14: 2_107,
        15: 2_411,
        16: 2_746,
        17: 3_115,
        18: 3_523,
        19: 3_973,
        20: 4_470,
        21: 5_018,
        22: 5_624,
        23: 6_291,
        24: 7_028,
        25: 7_842,
        26: 8_740,
        27: 9_730,
        28: 10_824,
        29: 12_031,
        30: 13_363,
        31: 14_833,
        32: 16_456,
        33: 18_247,
        34: 20_224,
        35: 22_406,
        36: 24_815,
        37: 27_473,
        38: 30_408,
        39: 33_648,
        40: 37_224,
        41: 41_171,
        42: 45_529,
        43: 50_339,
        44: 55_649,
        45: 61_512,
        46: 67_983,
        47: 75_127,
        48: 83_014,
        49: 91_721,
        50: 101_333,
        51: 111_945,
        52: 123_660,
        53: 136_594,
        54: 150_872,
        55: 166_636,
        56: 184_040,
        57: 203_254,
        58: 224_466,
        59: 247_886,
        60: 273_742,
        61: 302_288,
        62: 333_804,
        63: 368_599,
        64: 407_015,
        65: 449_428,
        66: 496_254,
        67: 547_953,
        68: 605_032,
        69: 668_051,
        70: 737_627,
        71: 814_445,
        72: 899_257,
        73: 992_895,
        74: 1_096_278,
        75: 1_210_421,
        76: 1_336_443,
        77: 1_475_581,
        78: 1_629_200,
        79: 1_798_808,
        80: 1_986_068,
        81: 2_192_818,
        82: 2_421_087,
        83: 2_673_114,
        84: 2_951_373,
        85: 3_258_594,
        86: 3_597_792,
        87: 3_972_294,
        88: 4_385_776,
        89: 4_842_295,
        90: 5_346_332,
        91: 5_902_831,
        92: 6_517_253,
        93: 7_195_629,
        94: 7_944_614,
        95: 8_771_558,
        96: 9_684_577,
        97: 10_692_629,
        98: 11_805_606,
        99: 13_034_431
    }
    for level, xp_threshold in xp_dict.items():
        if xp < xp_threshold:
            return level - 1
    return 99
                

async def setup(bot):
    await bot.add_cog(MessageXP(bot))