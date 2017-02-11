from discord.ext import commands
import json


class Service:
    """
    Service commands (owner only)
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    # Read config
    with open('config.json') as _data:
        _config = json.load(_data)
    _owner = _config['owner']

    # Execute
    async def _send(self, msg):
        await self.bot.say(msg)

    # List commands
    @commands.command(name="services", pass_context=True)
    async def _services(self):
        """List service commands."""
        funcs = dir(self)
        msg = "```List of {} commands:\n".format(self.__class__.__name__)
        for func in funcs:
            if func != "bot" and func[0] != "_":
                msg += func + "\n"
        msg += "```"
        await self._send(msg)

    # Commands
    @commands.command(pass_context=True, hidden=True)
    async def reload(self, ctx):
        # TODO: Probably I should do this check in other way...
        if ctx.message.author.id == self._owner:

            for extension in self._config['extensions']:
                try:
                    self.bot.unload_extension(extension['name'])
                    self.bot.load_extension(extension['name'])
                except Exception as e:
                    self._send('{} failed to load.\n{}: {}'.format(extension['name'], type(e).__name__, e))
                    print('{} failed to load.\n{}: {}'.format(extension['name'], type(e).__name__, e))
            await self._send("Reload complete!")
        else:
            await self._send("Access denied.")


def setup(bot):
    bot.add_cog(Service(bot))
