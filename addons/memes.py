from discord.ext import commands


class Memes:
    """
    Meme commands
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    # Execute
    async def _send(self, msg):
        await self.bot.say(msg)

    # List commands
    @commands.command()
    async def memes(self):
        """List memes."""
        msg = "`Usage: Kurisu, meme <name>`\n```List of memes:\n"
        db = self.bot.db.cursor()
        db.execute("SELECT * FROM memes")
        data = db.fetchall()
        for row in data:
            msg += row[0] + "\n"
        msg += "```"
        await self._send(msg)

    # Commands
    @commands.command()
    async def meme(self, name: str):
        """Shows meme. Usage: Kurisu, meme <name>"""
        db = self.bot.db.cursor()
        db.execute("SELECT * FROM memes WHERE name=?", (name,))
        row = db.fetchone()
        msg = row[1]
        db.close()
        await self._send(msg)


# Load the extension
def setup(bot):
    bot.add_cog(Memes(bot))
