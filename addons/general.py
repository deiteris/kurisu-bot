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

    def get_members(self, ctx, name):
        members = []
        for mem in ctx.message.server.members:
            # Limit number of results
            if name.lower() in mem.name.lower() and len(members) < 5:
                members.append(mem.name + "#" + mem.discriminator)
        return members

    async def get_member(self, ctx, name, members):
        if name.startswith("<@"):
            name = name.strip('<@?!#$%^&*>')
            member = ctx.message.server.get_member(name)
            return member
        else:
            if members:
                if len(members) > 3:
                    await self.bot.say("There are too many results. Please be more specific.\n\nHere is a list with suggestions:\n" + "\n".join(members))
                    return
                member = ctx.message.server.get_member_named(members[0])
                return member
            else:
                await self.send("No members were found and I don't have any clue who's that.")
                return

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
        """Helps you to google. Usage: Kurisu, google <query>"""
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
        embeded.add_field(name="Created on:", value=ctx.message.server.created_at.strftime('%d %B %Y at %H:%M UTC'), inline=True)
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

        members = self.get_members(ctx, name)

        member = await self.get_member(ctx, name, members)

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

        # TODO: Feels kinda bad but what else can I do?
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

        members = self.get_members(ctx, name)

        member = await self.get_member(ctx, name, members)

        if len(members) > 1:
            await self.send("There are more members you might be interested in:\n" + "\n".join(members) + "\n\n{}".format(member.avatar_url))
        else:
            await self.send(member.avatar_url)

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
        ctx.message.server.settings.update({'wiki_lang': lang})
        await self.send("`Wiki language has been set to {}`".format(lang))


def setup(bot):
    bot.add_cog(General(bot))
