#!/usr/bin/env python3

# Inspired by 916253 and ihaveamac/ihaveahax
# Codebase: https://github.com/916253/Kurisu
# Made just for fun, feel free to use

# Import dependencies
import os, sys
import json
import sqlite3
import discord
from datetime import datetime
from discord.ext import commands

description = """
ハロー, my name is Kurisu Makise.
Project source code: 
https://github.com/RIP95/kurisu-bot

Here is the list of available commands:
"""

# Set working directory to bot's folder
dir_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(dir_path)

prefixes = commands.when_mentioned_or('Kurisu, ', "kurisu, ", 'k.', 'K.')
bot = commands.Bot(command_prefix=prefixes, description=description, pm_help=None)

# Read config
if not os.path.isfile("config.json"):
    sys.exit("Set up your config.json file first!")

with open('config.json') as data:
    bot.config = json.load(data)

# Initialize db connection
bot.db = sqlite3.connect('main.db')
# Create tables for muted members and access roles. Necessary for basic functionality.
bot.db.execute('CREATE TABLE IF NOT EXISTS mutes (id integer NOT NULL primary key AUTOINCREMENT, member_id varchar, member_name varchar, mute_time integer, server_id varchar)')
bot.db.execute('CREATE TABLE IF NOT EXISTS roles (id integer NOT NULL primary key AUTOINCREMENT, role varchar, level int, serverid varchar)')
bot.db.commit()

# Global storages
# Roles
bot.access_roles = {}
# Mutes
bot.unmute_timers = {}
# Per server settings
bot.servers_settings = {}


# Doesn't change since bot is already running. No reason to put it in "events".
@bot.event
async def on_ready():

    # Used for 'uptime' command
    bot.start_time = datetime.today()

    print("{} has started!".format(bot.user.name))
    print("Current time is {}".format(bot.start_time))

    cursor = bot.db.cursor()
    for server in bot.servers:

        # Add server to access_roles storage
        bot.access_roles.update({server.id: {}})
        # Add server to unmute_timers storage
        bot.unmute_timers.update({server.id: {}})
        # Add server and default settings to servers_settings storage
        bot.servers_settings.update({server.id: {'wiki_lang': 'en'}})

        # Preload roles in storage
        cursor.execute("SELECT * FROM roles WHERE serverid={}".format(server.id))
        roles_data = cursor.fetchall()
        if roles_data:
            for row in roles_data:
                # row[0] - ID
                # row[1] - role name
                # row[2] - role level
                # row[3] - server id
                bot.access_roles[server.id].update({row[1]: row[2]})

        print("Connected to {} with {:,} members!".format(server.name, server.member_count))

    cursor.close()

    # Load extensions after we have connected to servers
    print("Loading addons:")
    for extension in bot.config['extensions']:
        try:
            bot.load_extension(extension['name'])
        except Exception as e:
            print('{} failed to load.\n{}: {}'.format(extension['name'], type(e).__name__, e))

    await bot.change_presence(game=discord.Game(name='Kurisu, help | El.Psy.Kongroo'))

# Set bot type in config. Will use token by default.
if bot.config['type'] == "user":
    bot.run(bot.config['email'], bot.config['password'])
else:
    bot.run(bot.config['token'])
