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

    # Temporary section for DB initialization
    # TODO: Make DB as a set of subcommands
    @commands.command(pass_context=True, hidden=True)
    async def db_init(self, ctx):
        # TODO: Probably I should do this check in other way...
        if ctx.message.author.id == self._owner:

            db = self.bot.db
            db.execute('CREATE TABLE memes (name text, image_url text)')
            memes = [
                ('hug', 'http://i.imgur.com/BlSC6Ek.jpg'),
                ('experiments', 'http://i.imgur.com/Ghsr77b.jpg'),
                ('bullshit', 'http://i.imgur.com/j2qrzWg.png'),
                ('thumbup', 'http://media.giphy.com/media/dbjM5lDyuZZS0/giphy.gif'),
                ('downvote', 'http://media.giphy.com/media/JD6D3c2rsQlyM/giphy.gif'),
                ('rip', 'Press F to pay respects.'),
                ('clap', 'http://i.imgur.com/UYbIZYs.gifv'),
                ('ayyy', 'http://i.imgur.com/bgvuHAd.png'),
                ('feelsbad', 'http://i.imgur.com/92Q62wf.jpg'),
                ('2d', 'http://i.imgur.com/aZ0ozAv.jpg'),
                ('bigsmoke', 'http://i.imgur.com/vo5l6Fo.jpg\nALL YOU HAD TO DO WAS FOLLOW THE DAMN GUIDE CJ!'),
                ('dio', 'http://i.imgur.com/QxxKeJ4.jpg\nYou thought it was Kurisu but it was me, DIO!'),
            ]
            db.executemany('INSERT INTO memes VALUES (?,?)', memes)
            db.execute('CREATE TABLE sounds (name text)')
            sounds = [
                ('laugh',), ('upa',), ('tina',), ('shave',),
                ('hentaikyouma',), ('timemachine',),
                ('realname',), ('madscientist',),
                ('dropthat',), ('tuturu',), ('tuturies',),
                ('tuturio',), ('angry',)
            ]
            db.executemany('INSERT INTO sounds VALUES (?)', sounds)
            db.commit()
            await self._send("Database initialization complete!")
            db.close()
        else:
            await self._send("Access denied.")


def setup(bot):
    bot.add_cog(Service(bot))
