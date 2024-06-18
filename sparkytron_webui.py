import asyncio
import discord
import os
import subprocess
from dotenv import load_dotenv
from src.bot import bot
from src.webui import flask_app


def run_flask_app(process):
    flask_port = os.getenv("flask_port")
    if not flask_port:
        flask_port = '5000'
    flask_app.bot_process = process
    flask_app.run(debug=True, use_reloader=False ,host='0.0.0.0', port=flask_port)

def main():
    load_dotenv()
    process = subprocess.Popen(["python", "sparkytron3000.py"])
    run_flask_app(process)


if __name__ == "__main__":
    main()