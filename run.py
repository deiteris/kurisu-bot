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

# Global roles storage
bot.access_roles = {}


# TESTING: Declare and register empty events, then work with them in "events" addon.
# I have no idea how it works since I haven't seen this usage and it's undocumented.
@bot.event
async def on_command_error(ecx, ctx): pass


@bot.event
async def on_server_join(server): pass


# @bot.event
# async def on_member_update(before, after): pass


@bot.event
async def on_member_join(member): pass


# @bot.event
# async def on_member_remove(member): pass


@bot.event
async def on_message(msg):

    if msg.author.bot:
        return

    await bot.process_commands(msg)


# Doesn't change since bot is already running. No reason to put it in "events".
@bot.event
async def on_ready():

    bot.start_time = datetime.today()
    cursor = bot.db.cursor()
    print("{} has started!".format(bot.user.name))
    print("Current time is {}".format(bot.start_time))
    for server in bot.servers:
        # Add server to access_roles storage
        bot.access_roles.update({server.id: {}})
        # Preload roles in storage
        cursor.execute("SELECT * FROM roles WHERE serverid={}".format(server.id))
        data = cursor.fetchall()
        if data:
            for row in data:
                # row[0] - ID
                # row[1] - role name
                # row[2] - role level
                # row[3] - server id
                bot.access_roles[server.id].update({row[1]: row[2]})
        # NOTE: custom storage for settings was made in API
        server.settings.update({'wiki_lang': "en"})
        print("Connected to {} with {:,} members!".format(server.name, server.member_count))
    cursor.close()
    await bot.change_presence(game=discord.Game(name='Kurisu, help | El.Psy.Kongroo'))

# Load extensions
print("Loading addons:")
for extension in bot.config['extensions']:
    try:
        bot.load_extension(extension['name'])
    except Exception as e:
        print('{} failed to load.\n{}: {}'.format(extension['name'], type(e).__name__, e))

# Set bot type in config. Will use token by default.
if bot.config['type'] == "user":
    bot.run(bot.config['email'], bot.config['password'])
else:
    bot.run(bot.config['token'])
