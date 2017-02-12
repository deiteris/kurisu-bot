import wikipedia
import asyncio
import re
import wolframalpha
import json
import discord
from discord.ext import commands
from random import uniform, randrange


class General:
    """
    General Chat Commands
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    # Read config
    with open('config.json') as _data:
        _config = json.load(_data)

    # Execute
    async def _send(self, msg):
        await self.bot.say(msg)

    # List commands
    @commands.command(name="general", pass_context=True)
    async def _general(self):
        """List general commands."""
        funcs = dir(self)
        msg = "```List of {} commands:\n".format(self.__class__.__name__)
        for func in funcs:
            if func != "bot" and func[0] != "_":
                msg += func + "\n"
        msg += "```"
        await self._send(msg)

    # Commands
    @commands.command(hidden=True)
    async def server(self):
        numbers = uniform(0, 10)
        await self._send(str(numbers))

    @commands.command(hidden=True)
    async def divergence(self):
        numbers = uniform(0, 10)
        await self._send(str(numbers))

    # Commands
    @commands.command(pass_context=True, hidden=True)
    async def randompin(self, ctx):
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
            await self._send('{1}\n{0}'.format(pins_attachment_list[i]['url'], pins_list[i]))
        else:
            await self._send(pins_list[i])

    @commands.command(hidden=True)
    async def google(self, *, text: str):
        """Let me google that for you"""
        query = re.sub('\s+', '+', text)
        await self._send('http://i.imgur.com/pIp93NT.jpg')
        await asyncio.sleep(2.5)
        await self._send('Is there anything you can do by yourself?\nhttps://lmgtfy.com/?q=' + query)

    # Credits to NotSoSuper#8800
    # https://github.com/NotSoSuper/NotSoBot
    @commands.command(hidden=True)
    async def wolfram(self, *, q: str):
        _wa = wolframalpha.Client(self._config['wolfram'])
        result = _wa.query(q)
        if result['@success'] == 'false':
            await self._send(':warning: `No results found on` <https://wolframalpha.com>')
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
            i = re.sub('\s+', '+', q)
            msg += '**Link:** https://www.wolframalpha.com/input/?i={}'.format(i)
            await self._send(msg)

    # Wiki command group
    @commands.group(pass_context=True, hidden=True)
    async def wiki(self, ctx):
        """
        Wiki command contains search and lang subcommands.

        Usage:
        Kurisu, wiki search Sample text
        Kurisu, wiki lang ru
        """
        if ctx.invoked_subcommand is None:
            # I am just too lazy to do a workaround for it, so let it be.
            msg = "```List of 'wiki' commands:\n"
            msg += "search\nlang```"
            await self._send(msg)

    @wiki.command(name="search", hidden=True)
    async def _wiki_search(self, *, query: str):
        wikipedia.set_lang(self.bot.wiki_lang_opt)
        try:
            msg = wikipedia.summary('{}'.format(query), sentences=10).strip()
        except wikipedia.exceptions.DisambiguationError as e:
            opt_list = ', '.join(e.options)
            await self.bot.say("```Requested article wasn't found. Try to be as clear as possible.\nI have few suggestions for you: " + opt_list + "```")
        await self._send(msg)

    @wiki.command(name="lang", hidden=True)
    async def _wiki_lang(self, lang: str):
        self.bot.wiki_lang_opt = '{}'.format(lang)
        await self._send("```Wiki language has been set to " + self.bot.wiki_lang_opt + "```")


def setup(bot):
    bot.add_cog(General(bot))
