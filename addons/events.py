import discord
import addons.checks as checks
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
        channel = ctx.message.channel

        if isinstance(ecx, commands.errors.CommandNotFound):
            await self.bot.send_message(channel, "I don't understand. Try `Kurisu, help`, baka!")
        elif isinstance(ecx, commands.errors.MissingRequiredArgument):
            formatter = commands.formatter.HelpFormatter()
            await self.bot.send_message(channel,
                                        "You are missing required arguments. See the usage:\n{}".format(
                                            formatter.format_help_for(ctx, ctx.command)[0]))
        elif isinstance(ecx, checks.errors.AccessDenied):
            await self.bot.send_message(channel, "Access denied.")

    async def on_server_join(self, server):
        self.bot.access_roles.update({server.id: {}})
        self.bot.unmute_timers.update({server.id: {}})
        self.bot.servers_settings.update({server.id: {'wiki_lang': "en"}})

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
