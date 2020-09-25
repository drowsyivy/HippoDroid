import discord # Imported from https://github.com/Rapptz/discord.py
import asyncio
from discord.ext import commands

import json
import logging
import base64
import os
import random

# Set up logger
discord_logger = logging.getLogger('HippoDroid')
discord_logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='hippodroid.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s'))
discord_logger.addHandler(handler)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s','%H:%M:%S'))
discord_logger.addHandler(handler)

# define 100 most common nouns
nouns = ['time', 'year', 'people', 'way', 'day', 'man', 'thing', 'woman', 'life', 'child', 'world', 'school', 'state',
'family', 'student', 'group', 'country', 'problem', 'hand', 'part', 'place', 'case', 'week', 'company', 'system',
'program', 'question', 'work', 'government', 'number', 'night', 'point', 'home', 'water', 'room', 'mother', 'area',
'money', 'story', 'fact', 'month', 'lot', 'right', 'study', 'book', 'eye', 'job', 'word', 'business', 'issue', 'side',
'kind', 'head', 'house', 'service', 'friend', 'father', 'power', 'hour', 'game', 'line', 'end', 'member', 'law', 'car',
'city', 'community', 'name', 'president', 'team', 'minute', 'idea', 'kid', 'body', 'information', 'back', 'parent',
'face', 'others', 'level', 'office', 'door', 'health', 'person', 'art', 'war', 'history', 'party', 'result', 'change',
'morning', 'reason', 'research', 'girl', 'guy', 'moment', 'air', 'teacher', 'force', 'education']

def save_requests(requests):
    with open('requests.json',"w") as requests_file:
        json.dump(requests, requests_file, indent=4) 

# check if the files exist
if not os.path.isfile('config.json'):
    discord_logger.error("You need to create a config file before using this bot! Check the bot")
if not os.path.isfile('requests.json'):
    discord_logger.info("Creating requests.json...")
    default_requests = {"pending": {}, "accepted": {}}
    save_requests(default_requests)

# Load data
with open('config.json') as config_file:    
    config = json.load(config_file)
with open('requests.json') as requests_file:
    requests = json.load(requests_file)
    # print(requests)

# Initialise bot settings
bot = commands.Bot(command_prefix=['!'], description=config['description'],
                    activity=discord.Game(name=config['status']),
                    pm_help=True, help_attrs=dict(hidden=True))

async def reply_id_generate():
    word_found = False
    if (len(requests['accepted']) + len(requests['pending'])) > 500000:
        discord_logger.error("Maximum IDs generated, aborting.")
        return None
    while not word_found:
        reply_id = f"{random.choice(nouns)}-{random.choice(nouns)}-{random.choice(nouns)}"
        if (reply_id not in requests['pending']) and (reply_id not in requests['accepted']):
            word_found = True
    return reply_id

async def resolve_pending_asker(reply_id: str):
    for pending in list(requests['pending'].items()):
        if pending[1][0] == reply_id:
            return pending[0]
    return None

async def resolve_accepted_asker(reply_id: str):
    for accepted in list(requests['accepted'].items()):
        if accepted[1][0] == reply_id:
            return accepted[0]
    return None

async def submit_request(message):
    if len(message.content) > 1800:
        await message.add_reaction("\u274C")
        await message.channel.send(f"**Sorry, but your request is too long. Please keep it under 1800 characters.**")
        return
    reply_id = await reply_id_generate()
    if reply_id == None:
        await message.channel.send(f"ERROR: The max number of hippo requests has been reached. Please try again later.")
        return
    requests["pending"][str(message.author.id)] = [reply_id, message.content]
    save_requests(requests)
    hidden_name = f"||{str(base64.b64encode(str.encode(str(message.author.id))))[2:-1]}||"
    mod_channel = bot.get_channel(config['mod_channel'])
    await mod_channel.send(f"**Incoming hippo request from {hidden_name}**\n\n{message.content}\n\n**This request has been assigned ID `{reply_id}`.**")
    await message.channel.send(f"**Your hippo request has been marked with reply ID ``{reply_id}`` and is now awaiting moderator approval.**")
    await message.add_reaction("\u2705")

async def submit_followup(message):
    if str(message.author.id) not in requests['accepted']:
        discord_logger.error("This was not supposed to happen.")
    if len(message.content) > 1800:
        await message.add_reaction("\u274C")
        await message.channel.send(f"**Sorry, but your follow-up is too long. Please keep it under 1800 characters.**")
        return
    public_channel = bot.get_channel(config['public_channel'])
    await public_channel.send(f"**Follow-up to ``{requests['accepted'][str(message.author.id)][0]}``:**\n\n{message.content}")
    await message.add_reaction("\u2705")

@bot.command(hidden=True)
async def accept(ctx, request_id: str = None):
    """
    Accepts a hippo request.
    """
    if (str(ctx.message.author.id) not in config['admins']) and (str(ctx.message.author.id) not in config['moderators']):
        await ctx.send('Sorry, but you can\'t do that!')
    else:
        if request_id == None:
            await ctx.send("Sorry, but I'll need the request ID to process this command.")
            return
        asker = await resolve_pending_asker(request_id)
        if asker == None:
            await ctx.send("Sorry. Doesn't look like that request ID exists.")
        else:
            requests['accepted'][asker] = requests['pending'][asker]
            requests['pending'].pop(asker)
            save_requests(requests)
            public_channel = bot.get_channel(config['public_channel'])
            await public_channel.send(f"**Anonymous question with reply ID ``{requests['accepted'][asker][0]}``:**\n\n{requests['accepted'][asker][1]}")
            asker_user = bot.get_user(int(asker))
            await asker_user.send(f"**Your request has been approved! Check the <#{config['public_channel']}> channel for further replies. " + 
                                    "You may receive notifications for replies through this bot, and you may provide " +
                                    "additional info anonymously by messaging this bot.\n\nTo close this request, use `!close` in this DM.**")
            await ctx.send(f"Request `{request_id}` successfully accepted!")

@bot.command(hidden=True)
async def reject(ctx, request_id: str = None, *, reason: str = None):
    """
    Rejects a hippo request.
    """
    if (str(ctx.message.author.id) not in config['admins']) and (str(ctx.message.author.id) not in config['moderators']):
        await ctx.send('Sorry, but you can\'t do that!')
    else:
        if request_id == None:
            await ctx.send("Sorry, but I'll need the request ID to process this command.")
            return
        asker = await resolve_pending_asker(request_id)
        if asker == None:
            await ctx.send("Sorry. Doesn't look like that request ID exists.")
        else:
            requests['pending'].pop(asker)
            save_requests(requests)
            asker_user = bot.get_user(int(asker))
            if reason == None:
                await asker_user.send("**Your request has been rejected. You may submit a new hippo request according to the guidelines specified in the exchange rules.**")
            else:
                await asker_user.send(f"**Your request has been rejected for the following reason:**\n\n{reason}\n\n**You may submit a new hippo request according to the guidelines specified in the exchange rules.**")
            await ctx.send(f"Request `{request_id}` successfully rejected!")

@bot.command(hidden=False)
async def close(ctx):
    """
    Closes your hippo request.
    """
    if str(ctx.message.author.id) in requests['accepted']:
        request_id = requests['accepted'][str(ctx.message.author.id)][0]
        requests['accepted'].pop(str(ctx.message.author.id))
        save_requests(requests)
        public_channel = bot.get_channel(config['public_channel'])
        await public_channel.send(f"**The anonymous question with ID `{request_id}` has been marked as answered.**")
        asker_user = bot.get_user(int(ctx.message.author.id))
        if str(ctx.message.channel.type) != "private":
            await ctx.message.delete()
            await asker_user.send("**You have closed your question. To make a new request, send a new direct message to this bot.\n\nPlease avoid closing anonymous questions in public chats.**")
        else:
            await asker_user.send("**You have closed your question. To make a new request, send a new direct message to this bot.**")
            await ctx.message.add_reaction("\u2705")

@bot.command(hidden=False)
async def reply(ctx, request_id: str = None, *, reply: str = None):
    """
    Reply to a hippo question.
    """
    if (request_id == None) or (reply == None):
        await ctx.send("Sorry, but I'll need the request ID and reply to process this command.")
        return
    if len(reply) > 1500:
        await message.channel.send(f"**Sorry, but your reply is too long. Please keep it under 1500 characters.**")
        return
    asker = await resolve_accepted_asker(request_id)
    if asker == None:
        await ctx.send("Sorry. Doesn't look like that request ID exists.")
    else:
        asker_user = bot.get_user(int(asker))
        await asker_user.send(f"**You have received a reply from {ctx.message.author.name}:**\n\n{reply}\n\nhttps://discord.com/channels/{ctx.message.channel.guild.id}/{ctx.message.channel.id}/{ctx.message.id}")
        await ctx.message.add_reaction("\u2705")

@bot.command(hidden=True, aliases=['resolveasker'])
async def resolve_asker(ctx, request_id: str = None):
    """
    Returns the masked asker of a given request.
    """
    if (str(ctx.message.author.id) not in config['admins']) and (str(ctx.message.author.id) not in config['moderators']):
        await ctx.send('Sorry, but you can\'t do that!')
    else:
        if request_id == None:
            await ctx.send("Sorry, but I'll need the request ID to process this command.")
            return
        asker = await resolve_pending_asker(request_id)
        if asker == None: asker = await resolve_accepted_asker(request_id)
        if asker == None:
            await ctx.send("Sorry. Doesn't look like that request ID exists.")
        else:
            hidden_name = f"||{str(base64.b64encode(str.encode(asker)))[2:-1]}||"
            await ctx.send(f'The asker of this question is {hidden_name}')

@bot.command(hidden=False, aliases=['inspireme'], description='Maximum of 100 words.')
async def inspire(ctx, number: int = 3):
    """
    Provides a string of a given number of randomly chosen words for inspiration.
    """
    if number > 100:
        number = 100
    reply = f'Here are the randomly chosen words you have asked for: \n\n**'
    while number > 0:
        reply += random.choice(nouns)
        number -= 1
        if number > 0:
            reply += ' '
    reply += '**\n\nI hope this inspires you to create something great!'
    await ctx.send(reply)

# Define console output when ready
@bot.event
async def on_ready():
    discord_logger.info('------')
    discord_logger.info('Logged in as:')
    discord_logger.info('Username: ' + bot.user.name)
    discord_logger.info('ID: ' + str(bot.user.id))
    discord_logger.info('------')

# Define all bot behaviours for DMs
@bot.event
async def on_message(message):
    # don't react to own messages lol
    if (message.author == bot.user):
        return

    if message.content.startswith("!"):
        await bot.process_commands(message)

    else:
        if str(message.channel.type) == "private":
            if str(message.author.id) in requests['pending']:
                await message.add_reaction("\u274C")
                await message.channel.send('**Your hippo request is already pending approval. Please wait while the moderators process your request.**')
            elif str(message.author.id) in requests['accepted']:
                await submit_followup(message)
            else:
                await submit_request(message)

# Start bot!
bot.run(config['token'])