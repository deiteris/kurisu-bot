import sqlite3
import json
import os, sys
from addons import utils
from addons.checks import checks
from discord.ext import commands
from discord import utils as discord


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
    @commands.command()
    @checks.is_access_allowed(required_level=9000)
    async def load(self, name: str):
        extension = "addons.{}".format(name)
        try:
            self.bot.load_extension(extension)
            print("{} loaded".format(extension))
        except Exception as e:
            print('{} failed to load.\n{}: {}'.format(extension, type(e).__name__, e))

    @commands.command()
    @checks.is_access_allowed(required_level=9000)
    async def unload(self, name: str):
        extension = "addons.{}".format(name)
        self.bot.unload_extension(extension)
        print("{} unloaded".format(extension))

    @commands.command()
    @checks.is_access_allowed(required_level=9000)
    async def reload(self):
        """Reloads addons, db and config (owner only)"""

        # Reload configuration file so we (probably) can apply some settings on the fly
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

    @commands.command()
    @checks.is_access_allowed(required_level=9000)
    async def switch(self):
        """Switches account between user and bot and shutting down bot (owner only)"""

        filename = 'config.json'

        if self.bot.config['type'] == 'user':
            self.bot.config['type'] = 'bot'
        else:
            self.bot.config['type'] = 'user'

        os.remove(filename)
        with open(filename, 'w') as file:
            json.dump(self.bot.config, file, indent=4)

        await self.send("Account switch completed! Restarting...")

        sys.exit()

    @commands.command()
    @checks.is_access_allowed(required_level=9000)
    async def shutdown(self):
        """This kills the bot (owner only)"""

        await self.send("Shutting down...")

        sys.exit()

    @commands.group(pass_context=True)
    async def roles(self, ctx):
        """Roles management (owner only)"""
        if ctx.invoked_subcommand is None:
            msg = "Have you ever tried `Kurisu, help roles` command? I suggest you do it now..."
            await self.send(msg)

    @roles.command(pass_context=True, name="list")
    @checks.is_access_allowed(required_level=3)
    async def roles_list(self, ctx):
        """Returns roles list for this server (Level 3)"""

        cursor = self.bot.db.cursor()

        if not await utils.db_check(self.bot, ctx.message, cursor, "roles"):
            return

        msg = "```List of roles:\n"
        cursor.execute("SELECT * FROM roles WHERE serverid=?", (ctx.message.server.id,))
        data = cursor.fetchall()
        cursor.close()
        if data:
            for row in data:
                msg += "ID: {} | Role name: {} | Level: {}\n".format(row[1], row[2], row[3])
        else:
            msg += "Empty"
        msg += "```"
        await self.send(msg)

    @roles.command(pass_context=True, name="add")
    @checks.is_access_allowed(required_level=3)
    async def roles_add(self, ctx, name: str, level: int):
        """Add role"""

        cursor = self.bot.db.cursor()

        if not await utils.db_check(self.bot, ctx.message, cursor, "roles"):
            return

        role = discord.get(ctx.message.server.roles, name=name)

        if role is None:
            print("Role wasn't found.")
            return

        db = self.bot.db

        record = (role.id, role.name.lower(), level, ctx.message.server.id)
        query = 'INSERT INTO roles(role_id, role, level, serverid) VALUES (?,?,?,?)'

        try:
            db.execute(query, record)
            db.commit()
            # Add role to storage
            self.bot.access_roles[ctx.message.server.id].update({role.id: level})
            await self.send("Your record has been successfully added.")
        except sqlite3.Error:
            await self.send("Failed to add new record.")

    @roles.command(pass_context=True, name="rm")
    @checks.is_access_allowed(required_level=3)
    async def roles_remove(self, ctx, name: str):
        """Remove role"""

        cursor = self.bot.db.cursor()

        if not await utils.db_check(self.bot, ctx, cursor, "roles"):
            return

        role = discord.get(ctx.message.server.roles, name=name)

        if role is None:
            print("Role wasn't found.")
            return

        db = self.bot.db

        record = (role.name.lower(), ctx.message.server.id)
        query = 'DELETE FROM roles WHERE role=? AND serverid=?'
        if db.execute(query, record).rowcount == 0:
            await self.send("Failed to remove this record.")
        else:
            db.commit()
            # Remove role from storage
            self.bot.access_roles[ctx.message.server.id].pop(role.id)
            await self.send("This record has been successfully removed.")

    @commands.group(pass_context=True)
    async def db(self, ctx):
        """Database management (owner only)"""
        if ctx.invoked_subcommand is None:
            msg = "Have you ever tried `Kurisu, help db` command? I suggest you do it now..."
            await self.send(msg)

    @db.command(name="init", pass_context=True)
    @checks.is_access_allowed(required_level=9000)
    async def db_init(self, ctx):
        """Initializes db (required on first start)"""

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

    @db.command(name="add")
    @checks.is_access_allowed(required_level=3)
    async def db_add(self, table: str, name: str, content: str):
        """Add record"""

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

    @db.command(name="edit")
    @checks.is_access_allowed(required_level=3)
    async def db_edit(self, table: str, name: str, column: str, value: str):
        """Edit record"""

        db = self.bot.db
        record = (name,)
        query = 'UPDATE {} SET {} = "{}" WHERE name=?'.format(table, column, value)
        if db.execute(query, record).rowcount == 0:
            await self.send("This record wasn't found.")
        else:
            db.commit()
            await self.send("This record has been successfully edited.")

    @db.command(name="rm")
    @checks.is_access_allowed(required_level=3)
    async def db_remove(self, table: str, name: str):
        """Remove record"""

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
