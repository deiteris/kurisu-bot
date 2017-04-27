import asyncio
from discord.ext import commands
from random import randrange


class Play:
    """
    Sound Commands
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    # Send message
    async def send(self, msg):
        await self.bot.say(msg)

    async def play_sound(self, msg, snd):
        vc = msg.author.voice_channel

        if str(vc) == "None":
            await self.bot.send_message(msg.channel, "Connect to voice channel first!")
            return

        bot = msg.server.get_member(self.bot.user.id)
        permissions = vc.permissions_for(bot)

        if not permissions.speak:
            await self.bot.send_message(msg.channel, "Failed to connect to channel. Reason: `muted`")
            return

        # Looks like checking if muted is enough even if we're lacking permissions or if it's afk channel
        #if not permissions.connect:
        #    await self.bot.send_message(msg.channel, "Failed to connect to channel. Reason: can't connect to this channel.")
        #    return

        voice_client = await self.bot.join_voice_channel(vc)

        if voice_client.is_connected():

            player = voice_client.create_ffmpeg_player('sounds/' + snd + '.mp3')
            player.start()

            while player.is_playing():
                await asyncio.sleep(0.2)
            else:
                await voice_client.disconnect()

    # List commands & play command group
    @commands.command()
    async def sounds(self):
        """List sounds."""
        msg = "`Usage: Kurisu, play <name>`\n```List of sounds:\n"
        db = self.bot.db.cursor()
        db.execute("SELECT * FROM sounds")
        data = db.fetchall()
        db.close()
        for row in data:
            msg += row[0] + "\n"
        msg += "random\n"
        msg += "```"
        await self.send(msg)

    @commands.command(pass_context=True)
    async def play(self, ctx, name: str):
        """Plays sound. Usage: Kurisu, play <name>"""
        db = self.bot.db.cursor()
        if name == "random":
            db.execute("SELECT * FROM sounds")
            data = db.fetchall()
            db.close()
            snd = []
            for row in data:
                snd.append(row[0])
            i = randrange(0, len(snd))

            await self.play_sound(ctx.message, snd[i])
        else:
            db.execute("SELECT * FROM sounds WHERE name=?", (name,))
            row = db.fetchone()
            db.close()
            snd = row[0]

            await self.play_sound(ctx.message, snd)


def setup(bot):
    bot.add_cog(Play(bot))
