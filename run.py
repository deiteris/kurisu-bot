#!/usr/bin/env python3

# Inspired by 916253 and ihaveamac/ihaveahax
# Codebase: https://github.com/916253/Kurisu
# Made just for fun, feel free to use

# Import dependencies
import os, sys
import discord
import json
import sqlite3
from discord.ext import commands
from random import randrange
from datetime import datetime

description = """
ハロー, my name is Kurisu Makise.
Project source code: 
https://github.com/RIP95/kurisu-bot

Here is the list of available commands:
"""

# Set working directory to bot's folder
dir_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(dir_path)

prefixes = commands.when_mentioned_or('Kurisu ', 'Kurisu, ', "kurisu ", "kurisu, ", '紅莉栖 ')
bot = commands.Bot(command_prefix=prefixes, description=description, pm_help=None)

bot.pruning = False  # used to disable leave logs if pruning, maybe.

# Read config
if not os.path.isfile("config.json"):
    sys.exit("Set up your config.json file first!")

with open('config.json') as data:
    bot.config = json.load(data)

#if not os.path.isfile("log.txt"):
#    with open("log.txt", "w") as log:
#        log.write("Log start\nFormat: Server:Channel -- [timestamp]: name - content | attachment url\n")

# Initialize db connection
bot.db = sqlite3.connect('main.db')

#def get_time_of_day(hour):
#    return {
#        0 <= hour < 6:  'Good evening',
#        6 <= hour < 12: 'Good morning',
#        12 <= hour < 18: 'Good afternoon',
#        18 <= hour < 24: 'Good evening'
#    }[True]


@bot.event
async def on_command_error(ecx, ctx):
    if isinstance(ecx, commands.errors.CommandNotFound):
        await bot.send_message(ctx.message.channel, "I don't understand. Try `Kurisu, help`, baka!")
    if isinstance(ecx, commands.errors.MissingRequiredArgument):
        formatter = commands.formatter.HelpFormatter()
        await bot.send_message(ctx.message.channel, "You are missing required arguments. See the usage:\n{}".format(formatter.format_help_for(ctx, ctx.command)[0]))


@bot.event
async def on_server_join(server):
    server.settings.update({'wiki_lang': "en"})

#@bot.event
#async def on_member_update(before, after):
#    if str(after.status) == "online" and str(after.bot) != "True" and str(before.status) == "offline":
#        time_of_day = get_time_of_day(datetime.today().hour)
#        opt_list = [time_of_day, "Welcome back", "Hello"]
#        i = randrange(0, len(opt_list))
#        await bot.send_message(before.server.default_channel, "{}, {}-san!".format(opt_list[i], str.capitalize(before.name)))


#@bot.event
#async def on_member_join(member):
#    if str(member.bot) != "True":
#        embeded = discord.Embed(title='New Labomem!', description='Labomem {} has joined our laboratory.'.format(str.capitalize(member.name)))
#        embeded.set_image(url='http://i.imgur.com/HYBdoFe.png')
#        await bot.send_message(member.server.default_channel, embed=embeded)


#@bot.event
#async def on_member_remove(member):
#    if str(member.bot) != "True":
#        await bot.send_message(member.server.default_channel, "Labomem {} has left our laboratory.".format(str.capitalize(member.name)))


@bot.event
async def on_message(msg):

    if msg.author.bot:
        return

    channel = msg.channel
    message = msg.content.lower()

    #try:
    #    server = msg.author.server
    #except AttributeError:
    #    server = "No server"

    # Log section
    #with open("log.txt", "a") as log:
    #    if msg.attachments:
    #        for attachment in msg.attachments:
    #            attachment_url = attachment['url']
    #        log.write('{}:{} -- [{}]: {} - {} | {}\n'.format(server, channel, msg.timestamp, msg.author, msg.clean_content, attachment_url))
    #    else:
    #        log.write('{}:{} -- [{}]: {} - {}\n'.format(server, channel, msg.timestamp, msg.author, msg.clean_content))

    # TODO: Probably needs to be done in some other way...
    if message == "kurisu":
        opt_list = ["Yes?", "Huh?", "What's the matter?"]
        i = randrange(0, len(opt_list))
        await bot.send_message(channel, opt_list[i])

    if message.startswith("kurisutina"):
        await bot.send_message(channel, "I told you there is no -tina!")
        return

    if message in ("nurupo", "nullpo", "ぬるぽ"):
        await bot.send_message(channel, "Gah!")
        return

    # Don't want to mess with roles for now
    if msg.content.startswith("<@&279725059952607233>"):
        await bot.send_message(channel, "I am not your assistant!")
        return

    await bot.process_commands(msg)


@bot.event
async def on_ready():

    bot.start_time = datetime.today()
    print("{} has started!".format(bot.user.name))
    print("Current time is {}".format(bot.start_time))
    for server in bot.servers:
        server.settings.update({'wiki_lang': "en"})
        print("Connected to {} with {:,} members!".format(server.name, server.member_count))
    await bot.change_presence(game=discord.Game(name='Kurisu, help | El.Psy.Kongroo'))

# Load extensions
print("Loading addons:")
for extension in bot.config['extensions']:
    try:
        bot.load_extension(extension['name'])
    except Exception as e:
        print('{} failed to load.\n{}: {}'.format(extension['name'], type(e).__name__, e))

bot.run(bot.config['token'])
