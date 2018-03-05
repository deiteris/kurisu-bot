from addons import utils
from discord.ext import commands
from random import choice


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

    # List commands
    @commands.command(pass_context=True)
    async def memes(self, ctx):
        """List memes."""

        cursor = self.bot.db.cursor()

        if not await utils.db_check(self.bot, ctx.message, cursor, "memes"):
            return

        msg = "`Usage: Kurisu, meme <name>`\n```List of memes:\n"
        cursor.execute("SELECT * FROM memes")
        data = cursor.fetchall()
        cursor.close()
        for row in data:
            msg += row[0] + "\n"
        msg += "random\n"
        msg += "```"
        await self.send(msg)

    # Commands
    @commands.command(pass_context=True)
    async def meme(self, ctx, *, name: str):
        """Shows meme. Usage: Kurisu, meme <name>"""

        cursor = self.bot.db.cursor()

        if not await utils.db_check(self.bot, ctx.message, cursor, "memes"):
            return

        if name == "random":
            cursor.execute("SELECT * FROM memes")
            data = cursor.fetchall()
            memes = []
            for row in data:
                memes.append(row[1])
            meme = choice(memes)
        else:
            cursor.execute("SELECT * FROM memes WHERE name=?", (name,))
            row = cursor.fetchone()
            if not row:
                await self.bot.send_message(ctx.message.channel, "Meme not found!")
                return
            meme = row[1]

        cursor.close()
        await self.send(meme)


# Load the extension
def setup(bot):
    bot.add_cog(Memes(bot))
