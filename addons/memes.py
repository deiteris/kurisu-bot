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
    @commands.command(name="memes", pass_context=True)
    async def _memes(self):
        """List meme commands."""
        funcs = dir(self)
        msg = "```List of {} commands:\n".format(self.__class__.__name__)
        for func in funcs:
            if func != "bot" and func[0] != "_":
                msg += func + "\n"
        msg += "```"
        await self._send(msg)

    # Commands
    @commands.command(hidden=True)
    async def hug(self):
        await self._send("http://i.imgur.com/BlSC6Ek.jpg")

    @commands.command(hidden=True)
    async def experiments(self):
        await self._send("http://i.imgur.com/Ghsr77b.jpg")

    @commands.command(hidden=True)
    async def troll(self):
        await self._send("http://i.imgur.com/afkdE2a.jpg")

    @commands.command(hidden=True)
    async def attention(self):
        await self._send("http://i.imgur.com/b7d6hV0.jpg")

    @commands.command(hidden=True)
    async def bullshit(self):
        await self._send("http://i.imgur.com/j2qrzWg.png")

    @commands.command(hidden=True)
    async def thumbup(self):
        await self._send("http://media.giphy.com/media/dbjM5lDyuZZS0/giphy.gif")

    @commands.command(hidden=True)
    async def downvote(self):
        await self._send("http://media.giphy.com/media/JD6D3c2rsQlyM/giphy.gif")

    @commands.command(hidden=True)
    async def lenny(self):
        await self._send("( ͡° ͜ʖ ͡°)")

    @commands.command(hidden=True)
    async def rip(self):
        await self._send("Press F to pay respects.")

    @commands.command(hidden=True)
    async def clap(self):
        await self._send("http://i.imgur.com/UYbIZYs.gifv")

    @commands.command(hidden=True)
    async def ayyy(self):
        await self._send("http://i.imgur.com/bgvuHAd.png")

    @commands.command(hidden=True)
    async def feelsbad(self):
        await self._send("http://i.imgur.com/92Q62wf.jpg")

    @commands.command(hidden=True)
    async def twod(self):
        await self._send("http://i.imgur.com/aZ0ozAv.jpg")

    @commands.command(hidden=True)
    async def dio(self, *, text: str):
        await self._send("http://i.imgur.com/QxxKeJ4.jpg\nYou thought it was {} but it was me, DIO!".format(text))

    @commands.command(hidden=True)
    async def bigsmoke(self):
        await self._send("http://i.imgur.com/vo5l6Fo.jpg\nALL YOU HAD TO DO WAS FOLLOW THE DAMN GUIDE CJ!")

    @commands.command(hidden=True)
    async def bigorder(self):
        await self._send("I’ll have two number 9s, a number 9 large, a number 6 with extra dip, a number 7, two number 45s, one with cheese, and a large soda.")


# Load the extension
def setup(bot):
    bot.add_cog(Memes(bot))
