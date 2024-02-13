import os
from dotenv import load_dotenv
from src.bot import bot

def main():
    load_dotenv()
    discord_token = os.getenv('discord_token')
    bot.run(discord_token, root_logger=True) 

if __name__ == "__main__":
    main()