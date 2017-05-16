import sqlite3
import json
from addons import utils
from discord.ext import commands


class Service:
    """
    Service commands (owner only)
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        self.checks = utils.PermissionChecks(bot)
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    # Send message
    async def send(self, msg):
        await self.bot.say(msg)

    # Commands
    @commands.command(pass_context=True)
    async def reload(self, ctx):
        """Reloads addons, db and config (owner only)"""

        if not await self.checks.check_perms(ctx.message, 9000):
            return

        # Reload configuration file so we can apply new settings on the fly
        # Might be useful
        with open('config.json') as data:
            self.bot.config = json.load(data)

        # TESTING: Potentially unsafe and might lead to data corruption.
        # Commit all changes and close connection before proceed
        self.bot.db.commit()
        self.bot.db.close()
        # Reinitilize connection to database
        self.bot.db = sqlite3.connect('main.db')

        # Reload extensions
        for extension in self.bot.config['extensions']:
            try:
                self.bot.unload_extension(extension['name'])
                self.bot.load_extension(extension['name'])
            except Exception as e:
                print('{} failed to load.\n{}: {}'.format(extension['name'], type(e).__name__, e))
        await self.send("Reload complete!")

    @commands.group(pass_context=True)
    async def roles(self, ctx):
        """Roles management (owner only)"""
        if ctx.invoked_subcommand is None:
            msg = "Have you ever tried `Kurisu, help roles` command? I suggest you do it now..."
            await self.send(msg)

    @roles.command(pass_context=True, name="init")
    async def roles_init(self, ctx):
        """Initializes roles (owner only)"""

        if not await self.checks.check_perms(ctx.message, 9000):
            return

        db = self.bot.db

        try:
            db.execute('CREATE TABLE IF NOT EXISTS roles (id integer NOT NULL primary key AUTOINCREMENT, role varchar, level int, serverid varchar)')
            roles = [
                ('commander', 3, '132200767799951360'), ('moderator', 2, '132200767799951360')
            ]
            db.executemany('INSERT INTO roles(role, level, serverid) VALUES (?,?,?)', roles)

            db.commit()

            # Put roles in storage
            # role[0] - role name
            # role[1] - access level
            for role in roles:
                self.bot.access_roles[ctx.message.server.id].update({role[0]: role[1]})

            await self.send("Roles have been initialized!")
        except sqlite3.Error:
            await self.send("Failed to initialize roles!")

    @roles.command(pass_context=True, name="list")
    async def roles_list(self, ctx):
        """Returns roles list for this server (Level 3)"""

        if not await self.checks.check_perms(ctx.message, 3):
            return

        cursor = self.bot.db.cursor()

        if not await utils.db_check(self.bot, ctx.message, cursor, "roles"):
            return

        msg = "```List of roles:\n"
        cursor.execute("SELECT * FROM roles WHERE serverid={}".format(ctx.message.server.id))
        data = cursor.fetchall()
        cursor.close()
        if data:
            for row in data:
                msg += "ID: {} | Role name: {} | Level: {}\n".format(row[0], row[1], row[2])
        else:
            msg += "Empty"
        msg += "```"
        await self.send(msg)

    @roles.command(pass_context=True, name="add")
    async def roles_add(self, ctx, name: str, level: int):
        """Add role"""

        if not await self.checks.check_perms(ctx.message, 3):
            return

        cursor = self.bot.db.cursor()

        if not await utils.db_check(self.bot, ctx.message, cursor, "roles"):
            return

        db = self.bot.db

        record = (name.lower(), level, ctx.message.server.id)
        query = 'INSERT INTO roles(role, level, serverid) VALUES (?,?,?)'

        try:
            db.execute(query, record)
            db.commit()
            # Add role to storage
            self.bot.access_roles[ctx.message.server.id].update({name.lower(): level})
            await self.send("Your record has been successfully added.")
        except sqlite3.Error:
            await self.send("Failed to add new record.")

    @roles.command(pass_context=True, name="rm")
    async def roles_remove(self, ctx, name: str):
        """Remove role"""

        if not await self.checks.check_perms(ctx.message, 3):
            return

        cursor = self.bot.db.cursor()

        if not await utils.db_check(self.bot, ctx, cursor, "roles"):
            return

        db = self.bot.db

        record = (name.lower(), ctx.message.server.id)
        query = 'DELETE FROM roles WHERE role=? AND serverid=?'
        if db.execute(query, record).rowcount == 0:
            await self.send("Failed to remove this record.")
        else:
            db.commit()
            # Remove role from storage
            self.bot.access_roles[ctx.message.server.id].pop(name.lower())
            await self.send("This record has been successfully removed.")

    @commands.group(pass_context=True)
    async def db(self, ctx):
        """Database management (owner only)"""
        if ctx.invoked_subcommand is None:
            msg = "Have you ever tried `Kurisu, help db` command? I suggest you do it now..."
            await self.send(msg)

    @db.command(name="init", pass_context=True)
    async def db_init(self, ctx):
        """Initializes db (required on first start)"""

        if not await self.checks.check_perms(ctx.message, 9000):
            return

        db = self.bot.db

        try:
            db.execute('CREATE TABLE IF NOT EXISTS memes (name varchar primary key, image_url text)')
            memes = [
                ('hug', 'https://i.imgur.com/BlSC6Ek.jpg'),
                ('experiments', 'https://i.imgur.com/Ghsr77b.jpg'),
                ('bullshit', 'https://i.imgur.com/j2qrzWg.png'),
                ('thumbup', 'https://media.giphy.com/media/dbjM5lDyuZZS0/giphy.gif'),
                ('downvote', 'https://media.giphy.com/media/JD6D3c2rsQlyM/giphy.gif'),
                ('rip', 'Press F to pay respects.'),
                ('clap', 'https://i.imgur.com/UYbIZYs.gifv'),
                ('ayyy', 'https://i.imgur.com/bgvuHAd.png'),
                ('feelsbad', 'https://i.imgur.com/92Q62wf.jpg'),
                ('2d', 'https://i.imgur.com/aZ0ozAv.jpg'),
                ('bigsmoke', 'https://i.imgur.com/vo5l6Fo.jpg\nALL YOU HAD TO DO WAS FOLLOW THE DAMN GUIDE CJ!'),
                ('dio', 'https://i.imgur.com/QxxKeJ4.jpg\nYou thought it was Kurisu but it was me, DIO!'),
            ]
            db.executemany('INSERT INTO memes VALUES (?,?)', memes)

            db.execute('CREATE TABLE IF NOT EXISTS sounds (name varchar primary key)')
            sounds = [
                ('laugh',), ('upa',), ('tina',), ('shave',),
                ('hentaikyouma',), ('timemachine',),
                ('realname',), ('madscientist',),
                ('dropthat',), ('tuturu',), ('tuturies',),
                ('tuturio',), ('angry',)
            ]
            db.executemany('INSERT INTO sounds VALUES (?)', sounds)

            db.execute('CREATE TABLE IF NOT EXISTS roles (id integer NOT NULL primary key AUTOINCREMENT, role varchar, level int, serverid varchar)')
            roles = [
                ('commander', 3, '132200767799951360'), ('moderator', 2, '132200767799951360')
            ]
            db.executemany('INSERT INTO roles(role, level, serverid) VALUES (?,?,?)', roles)

            db.commit()

            # Put roles in storage
            # role[0] - role name
            # role[1] - access level
            for role in roles:
                self.bot.access_roles[ctx.message.server.id].update({role[0]: role[1]})

            await self.send("Database has been initialized!")
        except sqlite3.Error:
            await self.send("Failed to initialize database!")

    @db.command(name="add", pass_context=True)
    async def db_add(self, ctx, table: str, name: str, content: str):
        """Add record"""

        if not await self.checks.check_perms(ctx.message, 3):
            return

        db = self.bot.db
        if table == "sounds":
            record = (name,)
            query = 'INSERT INTO {} VALUES (?)'.format(table)
        else:
            record = ('{}'.format(name), '{}'.format(content))
            query = 'INSERT INTO {} VALUES (?,?)'.format(table)

        try:
            db.execute(query, record)
            db.commit()
            await self.send("Your record has been successfully added.")
        except sqlite3.Error:
            await self.send("Failed to add new record.")

    @db.command(name="edit", pass_context=True)
    async def db_edit(self, ctx, table: str, name: str, column: str, value: str):
        """Edit record"""

        if not await self.checks.check_perms(ctx.message, 3):
            return

        db = self.bot.db
        record = (name,)
        query = 'UPDATE {} SET {} = "{}" WHERE name=?'.format(table, column, value)
        if db.execute(query, record).rowcount == 0:
            await self.send("This record wasn't found.")
        else:
            db.commit()
            await self.send("This record has been successfully edited.")

    @db.command(name="rm", pass_context=True)
    async def db_remove(self, ctx, table: str, name: str):
        """Remove record"""

        if not await self.checks.check_perms(ctx.message, 3):
            return

        db = self.bot.db
        record = (name,)
        query = 'DELETE FROM {} WHERE name=?'.format(table)
        if db.execute(query, record).rowcount == 0:
            await self.send("Failed to remove this record.")
        else:
            db.commit()
            await self.send("This record has been successfully removed.")


def setup(bot):
    bot.add_cog(Service(bot))
