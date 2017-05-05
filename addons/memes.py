import sqlite3
from discord.ext import commands
from random import randrange


class Memes:
    """
    Meme commands
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    # Send message
    async def send(self, msg):
        await self.bot.say(msg)

    # TODO: Move this to utils
    async def db_check(self, db):
        try:
            db.execute('SELECT 1 FROM memes')
            return True
        except sqlite3.Error:
            db.close()
            return False

    # List commands
    @commands.command()
    async def memes(self):
        """List memes."""

        db = self.bot.db.cursor()

        if not await self.db_check(db):
            await self.send("Database is not initialized. Use `Kurisu, db init` to perform initialization.")
            return

        msg = "`Usage: Kurisu, meme <name>`\n```List of memes:\n"
        db.execute("SELECT * FROM memes")
        data = db.fetchall()
        db.close()
        for row in data:
            msg += row[0] + "\n"
        msg += "random\n"
        msg += "```"
        await self.send(msg)

    # Commands
    @commands.command()
    async def meme(self, *, name: str):
        """Shows meme. Usage: Kurisu, meme <name>"""

        db = self.bot.db.cursor()

        if not await self.db_check(db):
            await self.send("Database is not initialized. Use `Kurisu, db init` to perform initialization.")
            return

        if name == "random":
            db.execute("SELECT * FROM memes")
            data = db.fetchall()
            memes = []
            for row in data:
                memes.append(row[1])
            i = randrange(0, len(memes))

            await self.send(memes[i])
        else:
            db.execute("SELECT * FROM memes WHERE name=?", (name,))
            row = db.fetchone()
            meme = row[1]

            await self.send(meme)

        db.close()


# Load the extension
def setup(bot):
    bot.add_cog(Memes(bot))
