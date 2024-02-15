import os
from dotenv import load_dotenv
from src.bot import bot

def main():
    load_dotenv()
    DISCORD_TOKEN = os.getenv('discord_token')
    bot.run(DISCORD_TOKEN, root_logger=True) 

if __name__ == "__main__":
    main()