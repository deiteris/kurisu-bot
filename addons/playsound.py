from discord.ext import commands
import asyncio
from random import randrange


class Play:
    """
    Sound Commands
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    # Execute
    # TODO: Requires some tweaking to match channel permissions (if muted, afk and etc)
    async def _play_sound(self, message, snd):
        vc = message.author.voice_channel
        if str(vc) == "None":
            await self.bot.send_message(message.channel, "```Connect to voice channel first!```")
            return
        voice_client = await self.bot.join_voice_channel(vc)
        if voice_client.is_connected():

            player = voice_client.create_ffmpeg_player('sounds/' + snd + '.mp3')
            player.start()

            while player.is_playing():
                await asyncio.sleep(0.2)
            else:
                await voice_client.disconnect()

    # List commands & play command group
    @commands.group(name="play", pass_context=True)
    async def _play(self, ctx):
        """List available sounds."""
        if ctx.invoked_subcommand is None:
            # this feels wrong...
            funcs = dir(self)
            msg = "```List of {} commands:\n".format(self.__class__.__name__)
            for func in funcs:
                if func != "bot" and func[0] != "_":
                    msg += func + "\n"
            msg += "```"
            await self.bot.send_message(ctx.message.channel, msg)

    # Play Subcommands
    @_play.command(pass_context=True)
    async def random(self, ctx):
        """Play random sound"""
        funcs = dir(self)
        msg = []
        for func in funcs:
            if func != "bot" and func[0] != "_":
                msg.append(func)

        i = randrange(0, len(msg))

        await self._play_sound(ctx.message, msg[i])

    @_play.command(pass_context=True, hidden=True)
    async def laugh(self, ctx):
        await self._play_sound(ctx.message, ctx.command.name)

    @_play.command(pass_context=True, hidden=True)
    async def upa(self, ctx):
        await self._play_sound(ctx.message, ctx.command.name)

    @_play.command(pass_context=True, hidden=True)
    async def tina(self, ctx):
        await self._play_sound(ctx.message, ctx.command.name)

    @_play.command(pass_context=True, hidden=True)
    async def shave(self, ctx):
        await self._play_sound(ctx.message, ctx.command.name)

    @_play.command(pass_context=True, hidden=True)
    async def hentaikyouma(self, ctx):
        await self._play_sound(ctx.message, ctx.command.name)

    @_play.command(pass_context=True, hidden=True)
    async def timemachine(self, ctx):
        await self._play_sound(ctx.message, ctx.command.name)

    @_play.command(pass_context=True, hidden=True)
    async def realname(self, ctx):
        await self._play_sound(ctx.message, ctx.command.name)

    @_play.command(pass_context=True, hidden=True)
    async def madscientist(self, ctx):
        await self._play_sound(ctx.message, ctx.command.name)

    @_play.command(pass_context=True, hidden=True)
    async def dropthat(self, ctx):
        await self._play_sound(ctx.message, ctx.command.name)

    @_play.command(pass_context=True, hidden=True)
    async def tuturu(self, ctx):
        await self._play_sound(ctx.message, ctx.command.name)

    @_play.command(pass_context=True, hidden=True)
    async def tuturies(self, ctx):
        await self._play_sound(ctx.message, ctx.command.name)

    @_play.command(pass_context=True, hidden=True)
    async def angry(self, ctx):
        await self._play_sound(ctx.message, ctx.command.name)


def setup(bot):
    bot.add_cog(Play(bot))
