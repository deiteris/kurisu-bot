import wikipedia
import asyncio
import re
import wolframalpha
import discord
import string
import hashlib
import utils
from datetime import datetime
from discord.ext import commands
from random import randrange, choice


class General:
    """
    General Chat Commands
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    # Send message
    async def send(self, msg):
        await self.bot.say(msg)

    # Commands
    @commands.command()
    async def ping(self):
        """Simple bot ping"""
        opt_list = ["Yes?", "Huh?", "What's the matter?"]
        i = randrange(0, len(opt_list))
        await self.send(opt_list[i])

    @commands.command()
    async def div(self):
        """Shows current wordline divergence"""
        date = datetime.today()
        calc = (date.day + date.month + date.year) / 13.35
        div = "{}.{}".format(date.month % 4, str(calc)[6:12])

        msg = "Current divergence is: {}".format(div)
        await self.send(msg)

    @commands.command()
    async def uptime(self):
        """Shows bot uptime"""
        uptime = datetime.today() - self.bot.start_time
        msg = "My uptime is {}".format(uptime)
        await self.send(msg)

    @commands.command(pass_context=True)
    async def randompin(self, ctx):
        """Shows random pinned message"""
        pins = await self.bot.pins_from(ctx.message.channel)

        if pins:
            i = randrange(0, len(pins))
            if not pins[i].attachments:
                pins[i].attachments = [{'url': ""}]
            await self.send("{}: {} {}".format(pins[i].author, pins[i].content, pins[i].attachments[0]['url']))
        else:
            await self.send("There are no pinned messages in this channel!")

    @commands.command()
    async def passgen(self, length: int):
        """Password generator"""
        letters = string.ascii_letters
        digits = string.digits
        chars = letters + digits + "!@#$%^&()\/|"
        i = 0
        password = "Your password: "

        while i < length:
            i += 1
            password += "".join(choice(chars))
        await self.send(password)

    @commands.command()
    async def google(self, *, query: str):
        """Helps you to google"""
        msg = re.sub('\s+', '+', query)
        await self.send('http://i.imgur.com/pIp93NT.jpg')
        await asyncio.sleep(2.5)
        await self.send('Is there anything you can do by yourself?\nhttps://lmgtfy.com/?q={}'.format(msg))

    @commands.group(pass_context=True)
    async def hash(self, ctx):
        """Set of hash commands"""
        if ctx.invoked_subcommand is None:
            msg = "Have you ever tried `Kurisu, help hash` command? I suggest you do it now..."
            await self.send(msg)

    @hash.command(name='md5')
    async def hash_md5(self, *, txt: str):
        """Hash input with MD5"""
        output = hashlib.md5(txt.encode()).hexdigest()
        await self.send('MD5: {}'.format(output))

    @hash.command(name='sha1')
    async def hash_sha1(self, *, txt: str):
        """Hash input with SHA1"""
        output = hashlib.sha1(txt.encode()).hexdigest()
        await self.send('SHA1: {}'.format(output))

    @hash.command(name='sha256')
    async def hash_sha256(self, *, txt: str):
        """Hash input with SHA256"""
        output = hashlib.sha256(txt.encode()).hexdigest()
        await self.send('SHA256: {}'.format(output))

    @hash.command(name='sha512')
    async def hash_sha512(self, *, txt: str):
        """Hash input with SHA512"""
        output = hashlib.sha512(txt.encode()).hexdigest()
        await self.send('SHA512: {}'.format(output))

    @commands.command(pass_context=True)
    async def react(self, ctx, target: str, *, word: str):
        """React to message with regional indicators"""

        # Emojis dictionary
        emojis = {
            "a": u"\U0001F1E6", "b": u"\U0001F1E7", "c": u"\U0001F1E8", "d": u"\U0001F1E9", "e": u"\U0001F1EA",
            "f": u"\U0001F1EB", "g": u"\U0001F1EC", "h": u"\U0001F1ED", "i": u"\U0001F1EE", "j": u"\U0001F1EF",
            "k": u"\U0001F1F0", "l": u"\U0001F1F1", "m": u"\U0001F1F2", "n": u"\U0001F1F3", "o": u"\U0001F1F4",
            "p": u"\U0001F1F5", "q": u"\U0001F1F6", "r": u"\U0001F1F7", "s": u"\U0001F1F8", "t": u"\U0001F1F9",
            "u": u"\U0001F1FA", "v": u"\U0001F1FB", "w": u"\U0001F1FC", "x": u"\U0001F1FD", "y": u"\U0001F1FE",
            "z": u"\U0001F1FF",
            "0": "\u0030\u20E3", "1": "\u0031\u20E3", "2": "\u0032\u20E3", "3": "\u0033\u20E3",
            "4": "\u0034\u20E3", "5": "\u0035\u20E3", "6": "\u0036\u20E3", "7": "\u0037\u20E3",
            "8": "\u0038\u20E3", "9": "\u0039\u20E3"
        }

        # Additional emojis dictionary in addition to reaction
        dictionary = {
            "pin": u'\U0001F4CC', "purge": u'\U0001F525', "nice": u'\U0001F44D',
            "nevah": u'\U00002122', "so0n": u'\U00002122', "ok": u'\U0001F197'
        }

        async def react_to(msg, bot, reaction):
            letters = re.sub('\s+', '', reaction)
            letters = list(letters)

            for letter in letters:
                await bot.add_reaction(msg, emojis[letter.lower()])
            if reaction in dictionary:
                await bot.add_reaction(msg, dictionary[reaction.lower()])

        if target == "me":
            await react_to(ctx.message, self.bot, word)
            return

        # Use bot API capabilities
        #try:
        #    message = await self.bot.get_message(ctx.message.channel, msg_id)
        #    for letter in letters:
        #        await self.bot.add_reaction(message, emojis[letter.lower()])
        #except discord.NotFound:
        #    await self.send('Message not found!')

        # Backward compatibility if bot runs as user
        async for message in self.bot.logs_from(ctx.message.channel, limit=70):
            if str(message.id) == target:
                await react_to(message, self.bot, word)
                return

    # Credits to NotSoSuper#8800
    # https://github.com/NotSoSuper/NotSoBot
    @commands.command()
    async def wolfram(self, *, query: str):
        """Provides access to wolframalpha computational knowledge engine"""
        wa = wolframalpha.Client(self.bot.config['wolfram'])
        result = wa.query(query)
        if result['@success'] == 'false':
            await self.send(':warning: `No results found on` <https://wolframalpha.com>')
        else:
            msg = ''
            for pod in result.pods:
                if int(pod['@numsubpods']) > 1:
                    for sub in pod['subpod']:
                        subpod_text = sub['plaintext']
                        if subpod_text is None:
                            continue
                        msg += '**{0}**: `{1}`\n'.format(pod['@title'], subpod_text)
                else:
                    subpod_text = pod['subpod']['plaintext']
                    if subpod_text is None:
                        continue
                    msg += '**{0}**: `{1}`\n'.format(pod['@title'], subpod_text)
            i = re.sub('\s+', '+', query)
            msg += '**Link:** https://www.wolframalpha.com/input/?i={}'.format(i)
            await self.send(msg)

    @commands.command(pass_context=True)
    async def server(self, ctx):
        """Shows server info"""
        roles = str(len(ctx.message.server.roles))
        emojis = str(len(ctx.message.server.emojis))
        channels = str(len(ctx.message.server.channels))

        embeded = discord.Embed(title=ctx.message.server.name, description='Server Info', color=0xEE8700)
        embeded.set_thumbnail(url=ctx.message.server.icon_url)
        embeded.add_field(name="Created on:", value=ctx.message.server.created_at.strftime('%d %B %Y at %H:%M UTC'), inline=False)
        embeded.add_field(name="Server ID:", value=ctx.message.server.id, inline=False)
        embeded.add_field(name="Users on server:", value=ctx.message.server.member_count, inline=True)
        embeded.add_field(name="Server owner:", value=ctx.message.server.owner, inline=True)

        embeded.add_field(name="Default Channel:", value=ctx.message.server.default_channel, inline=True)
        embeded.add_field(name="Server Region:", value=ctx.message.server.region, inline=True)
        embeded.add_field(name="Verification Level:", value=ctx.message.server.verification_level, inline=True)

        embeded.add_field(name="Role Count:", value=roles, inline=True)
        embeded.add_field(name="Emoji Count:", value=emojis, inline=True)
        embeded.add_field(name="Channel Count:", value=channels, inline=True)

        await self.bot.say(embed=embeded)

    @commands.command(pass_context=True)
    async def user(self, ctx, *, name: str):
        """Shows user info"""

        members = utils.get_members(ctx, name)

        if len(members) > 4:
            await self.bot.say("There are too many results. Please be more specific.\n\nHere is a list with suggestions:\n" + "\n".join(members))
            return

        member = await utils.get_member(self.bot, ctx, name, members)

        if member is None:
            return

        roles = []
        server_counter = 0

        for role in member.roles:
            roles.append(role.name)

        for server in self.bot.servers:
            if server.get_member(member.id) is not None:
                server_counter += 1

        # 0 is always @everyone
        del roles[0]

        created_time_ago = datetime.today() - member.created_at
        joined_time_ago = datetime.today() - member.joined_at

        # TODO: Feels like this can be done in some other way
        created_case = "days" if created_time_ago.days > 1 else "day"
        joined_case = "days" if joined_time_ago.days > 1 else "day"

        created_at = "{} ({} {} ago)".format(member.created_at.strftime('%d %B %Y at %H:%M UTC'), created_time_ago.days, created_case)
        joined_at = "{} ({} {} ago)".format(member.joined_at.strftime('%d %B %Y at %H:%M UTC'), joined_time_ago.days, joined_case)

        embeded = discord.Embed(title=member.name + "#" + member.discriminator, description='Member Info', color=0xEE8700)
        embeded.set_thumbnail(url=member.avatar_url)
        embeded.add_field(name="Nickname:", value=member.nick, inline=True)
        embeded.add_field(name="ID:", value=member.id, inline=True)
        embeded.add_field(name="Shared servers:", value=server_counter, inline=False)
        embeded.add_field(name="Created account:", value=created_at, inline=False)
        embeded.add_field(name="Joined server:", value=joined_at, inline=False)

        # TODO: probably this can be shortened
        if not roles:
            embeded.add_field(name="Roles: ({})".format(len(roles)), value="None", inline=False)
        else:
            embeded.add_field(name="Roles: ({})".format(len(roles)), value=", ".join(roles), inline=False)

        if len(members) > 1:
            await self.bot.say("There are more members you might be interested in:\n" + "\n".join(members), embed=embeded)
        else:
            await self.bot.say(embed=embeded)

    @commands.command(pass_context=True)
    async def avatar(self, ctx, *, name: str):
        """Shows user avatar url"""

        members = utils.get_members(ctx, name)

        if len(members) > 4:
            await self.bot.say("There are too many results. Please be more specific.\n\nHere is a list with suggestions:\n" + "\n".join(members))
            return

        member = await utils.get_member(self.bot, ctx, name, members)

        if member is None:
            return

        if not member.avatar_url:
            await self.send("This user doesn't have avatar.")
            return

        if len(members) > 1:
            await self.send("There are more members you might be interested in:\n" + "\n".join(members) + "\n\n{}".format(member.avatar_url))
        else:
            await self.send("Take a closer look at this avatar\n{}".format(member.avatar_url))

    # Wiki command group
    @commands.group(pass_context=True)
    async def wiki(self, ctx):
        """
        Wiki command contains search and lang subcommands.

        Usage:
        Kurisu, wiki search Sample text
        Kurisu, wiki lang ru
        """
        if ctx.invoked_subcommand is None:
            msg = "Have you ever tried `Kurisu, help wiki` command? I suggest you do it now..."
            await self.send(msg)

    @wiki.command(name="search", pass_context=True)
    async def wiki_search(self, ctx, *, query: str):
        """Searches article on wiki"""
        wikipedia.set_lang(ctx.message.server.settings['wiki_lang'])
        try:
            msg = wikipedia.summary('{}'.format(query), sentences=10).strip()
            await self.send(msg)
        except wikipedia.exceptions.DisambiguationError as e:
            opt_list = ', '.join(e.options)
            await self.send("Requested article wasn't found. Try to be as clear as possible.\n\n"
                            "I have few suggestions for you: `{}`".format(opt_list))

    @wiki.command(name="lang", pass_context=True)
    async def wiki_lang(self, ctx, lang: str):
        """Sets wiki language. Format: en"""
        ctx.message.server.settings.update({'wiki_lang': lang})
        await self.send("`Wiki language has been set to {}`".format(lang))


def setup(bot):
    bot.add_cog(General(bot))
