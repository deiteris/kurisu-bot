import wikipedia
import asyncio
import re
import wolframalpha
import discord
import string
import hashlib
from datetime import datetime
from discord.ext import commands
from random import uniform, randrange, choice


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
    async def divergence(self):
        """Shows current wordline divergence"""
        numbers = uniform(0, 10)
        divergence = str(numbers)
        msg = "Current wordline divergence is {}".format(divergence[:8])
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
        # Made in complex but simply works!
        pins_list = []
        pins_attachment_list = []
        pins = await self.bot.pins_from(ctx.message.channel)
        # Get pins
        for pin in pins:
            try:
                # Check if we have attachments for a pin
                if pin.attachments:
                    for attachment in pin.attachments:
                        # Add image to pins_attachment_list array
                        pins_attachment_list.append(attachment)
                else:
                    # TODO: Usually we deal with only one attachment per message, so it will work perfectly.
                    # TODO: But what if we have more than one in the same message... Is it even possible?
                    # Keep arrays equal. Fill space with zero.
                    pins_attachment_list.append(0)
                # Add message to pins_list array
                pins_list.append(pin.content)
            except discord.HTTPException as e:
                print('Pin {} failed to load.'.format(e))
        i = randrange(0, len(pins_list))

        # Since we have equal arrays we can simply check if the same array index has zero and respond accordingly
        if pins_attachment_list[i] != 0:
            await self.send('{1}\n{0}'.format(pins_attachment_list[i]['url'], pins_list[i]))
        else:
            await self.send(pins_list[i])

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
        """Helps you to google. Usage: Kurisu, google <query>"""
        msg = re.sub('\s+', '+', query)
        await self.send('http://i.imgur.com/pIp93NT.jpg')
        await asyncio.sleep(2.5)
        await self.send('Is there anything you can do by yourself?\nhttps://lmgtfy.com/?q={}'.format(msg))

    @commands.group(pass_context=True)
    async def hash(self, ctx):
        """Hash input with MD5"""
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

    @wiki.command(name="search")
    async def wiki_search(self, *, query: str):
        wikipedia.set_lang(self.bot.wiki_lang_opt)
        try:
            msg = wikipedia.summary('{}'.format(query), sentences=10).strip()
        except wikipedia.exceptions.DisambiguationError as e:
            opt_list = ', '.join(e.options)
            await self.send("Requested article wasn't found. Try to be as clear as possible.\n\n"
                            "I have few suggestions for you: `{}`".format(opt_list))
        await self.send(msg)

    @wiki.command(name="lang")
    async def wiki_lang(self, lang: str):
        self.bot.wiki_lang_opt = '{}'.format(lang)
        await self.send("`Wiki language has been set to {}`".format(self.bot.wiki_lang_opt))


def setup(bot):
    bot.add_cog(General(bot))
