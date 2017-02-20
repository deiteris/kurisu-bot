from discord.ext import commands
import sqlite3


class Service:
    """
    Service commands (owner only)
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    # Send message
    async def send(self, msg):
        await self.bot.say(msg)

    # Commands
    @commands.command(pass_context=True)
    async def reload(self, ctx):
        """Reloads extensions (owner only)"""
        # TODO: Probably I should do this check in other way...
        if ctx.message.author.id == self.bot.config['owner']:

            for extension in self.bot.config['extensions']:
                try:
                    self.bot.unload_extension(extension['name'])
                    self.bot.load_extension(extension['name'])
                except Exception as e:
                    self.send('{} failed to load.\n{}: {}'.format(extension['name'], type(e).__name__, e))
                    print('{} failed to load.\n{}: {}'.format(extension['name'], type(e).__name__, e))
            await self.send("Reload complete!")
        else:
            await self.send("Access denied.")

    # Temporary section for DB initialization
    # TODO: Convert db_init to set of subcommands
    @commands.group(pass_context=True)
    async def db(self, ctx):
        """Database management (owner only)"""
        if ctx.invoked_subcommand is None:
            msg = "Have you ever tried `Kurisu, help db` command? I suggest you do it now..."
            await self.send(msg)

    @db.command(name="init", pass_context=True)
    async def db_init(self, ctx):
        if ctx.message.author.id == self.bot.config['owner']:
            db = self.bot.db
            db.execute('CREATE TABLE memes (name varchar primary key, image_url text)')
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
            db.execute('CREATE TABLE sounds (name varchar primary key)')
            sounds = [
                ('laugh',), ('upa',), ('tina',), ('shave',),
                ('hentaikyouma',), ('timemachine',),
                ('realname',), ('madscientist',),
                ('dropthat',), ('tuturu',), ('tuturies',),
                ('tuturio',), ('angry',)
            ]
            db.executemany('INSERT INTO sounds VALUES (?)', sounds)
            db.commit()
            await self.send("Database initialization complete!")
        else:
            await self.send("Access denied.")

    @db.command(name="add", pass_context=True)
    async def db_add(self, ctx, table: str, name: str, content: str):
        if ctx.message.author.id == self.bot.config['owner']:
            db = self.bot.db
            record = ('{}'.format(name), '{}'.format(content))
            query = 'INSERT INTO {} VALUES (?,?)'.format(table)
            try:
                db.execute(query, record)
                db.commit()
                await self.send("Your record has been successfully added.")
            except sqlite3.Error:
                await self.send("Failed to add new record.")
        else:
            await self.send("Access denied.")

    @db.command(name="rm", pass_context=True)
    async def db_remove(self, ctx, table: str, name: str):
        if ctx.message.author.id == self.bot.config['owner']:
            db = self.bot.db
            record = ('{}'.format(name),)
            query = 'DELETE FROM {} WHERE name=?'.format(table)
            if db.execute(query, record).rowcount == 0:
                await self.send("Failed to remove this record.")
            else:
                db.commit()
                await self.send("This record has been successfully removed.")
        else:
            await self.send("Access denied.")


def setup(bot):
    bot.add_cog(Service(bot))
