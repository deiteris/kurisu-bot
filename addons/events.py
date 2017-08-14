import discord
from datetime import datetime
from random import randint
from discord.ext import commands


class Events:
    """
    Events addon
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    async def on_command_error(self, ecx, ctx):
        if isinstance(ecx, commands.errors.CommandNotFound):
            await self.bot.send_message(ctx.message.channel, "I don't understand. Try `Kurisu, help`, baka!")
        if isinstance(ecx, commands.errors.MissingRequiredArgument):
            formatter = commands.formatter.HelpFormatter()
            await self.bot.send_message(ctx.message.channel,
                                        "You are missing required arguments. See the usage:\n{}".format(
                                            formatter.format_help_for(ctx, ctx.command)[0]))

    async def on_server_join(self, server):
        self.bot.access_roles.update({server.id: {}})
        self.bot.unmute_timers.update({server.id: {}})
        self.bot.servers_settings.update({server.id: {'wiki_lang': "en"}})
        for member in server.members:
            if member.id not in self.bot.member_last_seen:
                if member.status is not discord.Status.offline:
                    self.bot.member_last_seen.update({member.id: member.status})
                else:
                    self.bot.member_last_seen.update({member.id: datetime.today().strftime('%d %B %Y at %H:%M UTC+3')})

    async def on_member_join(self, member):

        if member.id not in self.bot.member_last_seen:
            self.bot.member_last_seen.update({member.id: member.status})

        steins_gate = "213420119034953729"

        if member.server.id == steins_gate:
            RCgamer77 = "RCgamer77#0099"
            embeded = discord.Embed(title="A new member has come to Steins;Gate church!", description='Member Info',
                                    color=0xEE8700)
            embeded.set_thumbnail(url=member.avatar_url)
            embeded.add_field(name="Name:", value=member.name, inline=True)
            embeded.add_field(name="ID:", value=member.id, inline=True)
            embeded.add_field(name="Created account:", value=member.created_at.strftime('%d-%m-%Y %H:%M:%S'), inline=True)
            embeded.set_image(url="https://i.imgur.com/Wj57Pe2.jpg")
            await self.bot.send_message(member.server.get_member_named(RCgamer77), embed=embeded)

    async def on_member_update(self, before, after):
        if after.status is discord.Status.offline:
            print("User went offline")
            self.bot.member_last_seen.update({after.id: datetime.today().strftime('%d %B %Y at %H:%M UTC+3')})
        else:
            print("User went online")
            self.bot.member_last_seen.update({after.id: after.status})

    async def on_message(self, msg):

        if msg.author.bot:
            return

        channel = msg.channel
        content = msg.content.lower()

        if content.startswith("kurisutina"):
            await self.bot.send_message(channel, "I told you there is no -tina!")
            return

        if content in ("nurupo", "nullpo", "ぬるぽ"):
            if randint(0, 10) > 5:
                await self.bot.send_message(channel, "Gah!")
            return


def setup(bot):
    bot.add_cog(Events(bot))
