import asyncio
import discord
import os
import subprocess
import sys
from dotenv import load_dotenv
from src.bot import bot
from src.webui import flask_app
from waitress import serve

def get_flask_app(process):
    flask_app.bot_process = process
    flask_app.secret_key = "woaoaoahaowhawoiahoahhhhhh"
    return flask_app

def main():
    load_dotenv()
    flask_port = os.getenv("flask_port")
    if not flask_port:
        flask_port = '5000'
    process = subprocess.Popen([sys.executable, "sparkytron3000.py"])
    flask_app = get_flask_app(process)
    serve(flask_app, host='0.0.0.0', port=flask_port)
    
if __name__ == "__main__":
    main()