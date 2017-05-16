import discord
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
        server.settings.update({'wiki_lang': "en"})

    # async def on_member_update(before, after):
    #    if str(after.status) == "online" and str(after.bot) != "True" and str(before.status) == "offline":
    #        time_of_day = get_time_of_day(datetime.today().hour)
    #        opt_list = [time_of_day, "Welcome back", "Hello"]
    #        i = randrange(0, len(opt_list))
    #        await bot.send_message(before.server.default_channel, "{}, {}-san!".format(opt_list[i], str.capitalize(before.name)))

    async def on_member_join(self, member):
        steins_gate = "213420119034953729"

        if member.server.id == steins_gate:
            RCgamer77 = "RCgamer77#0099"
            # Me = "Emojikage#3095"
            embeded = discord.Embed(title="A new member has come to Steins;Gate church!", description='Member Info',
                                    color=0xEE8700)
            embeded.set_thumbnail(url=member.avatar_url)
            embeded.add_field(name="Name:", value=member.name, inline=True)
            embeded.add_field(name="ID:", value=member.id, inline=True)
            embeded.add_field(name="Created account:", value=member.created_at.strftime('%d-%m-%Y %H:%M:%S'), inline=True)
            embeded.set_image(url="https://i.imgur.com/Wj57Pe2.jpg")
            await self.bot.send_message(member.server.get_member_named(RCgamer77), embed=embeded)
            # await self.bot.send_message(member.server.get_member_named(Me), embed=embeded)

    # if str(member.bot) != "True":
    #        embeded = discord.Embed(title='New Labomem!', description='Labomem {} has joined our laboratory.'.format(str.capitalize(member.name)))
    #        embeded.set_image(url='http://i.imgur.com/HYBdoFe.png')
    #        await bot.send_message(member.server.default_channel, embed=embeded)


    # async def on_member_remove(member):
    #    if str(member.bot) != "True":
    #        await bot.send_message(member.server.default_channel, "Labomem {} has left our laboratory.".format(str.capitalize(member.name)))

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
