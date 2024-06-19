import logging
import os
import subprocess
import sys

from flask import Flask, render_template, request, flash

logger = logging.getLogger("bot")
flask_app = Flask(__name__, template_folder='../flask_templates')

def read_env(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            key_value_pairs = {}
            for line in file:
                try:
                    key, value = line.strip().split('=')
                    key = key.strip()
                    value = value.strip()[1:-1]
                    key_value_pairs[key] = value
                except:
                    print("This line isnt a kv pair")
        return key_value_pairs
    else:
        return None

@flask_app.route('/', methods=['GET', 'POST'])
async def index():
    key_value_pairs = read_env('.env')
    if not key_value_pairs:
        logger.warn("No .env file found! Copying defaults.")
        key_value_pairs = read_env('.env_default')
    form_dict = {}
    if request.method == 'POST':
        if key_value_pairs:
            for form_name in key_value_pairs.keys():
                form_dict[form_name] = request.form[form_name]
        with open('.env', 'w') as file:
            for key, value in form_dict.items():
                file.write(f"{key}='{value}'\n")
        print(form_dict)
        flask_app.bot_process.terminate()
        flask_app.bot_process = subprocess.Popen([sys.executable, "sparkytron3000.py"])
        message = "Variables Updated!"
        flash(message)
    return render_template('index.html', key_value_pairs = key_value_pairs)

