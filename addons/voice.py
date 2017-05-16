import asyncio
import discord
import shutil
from addons import utils
from discord.ext import commands
from random import randrange

if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('/usr/lib/libopus.so')


class VoiceEntry:

    current_position = 0
    is_command = False

    def __init__(self, message, player):
        self.requester = message.author
        self.channel = message.channel
        self.player = player

    def __str__(self):
        fmt = '*{0.title}* uploaded by {0.uploader} and requested by {1.display_name}'
        duration = self.player.duration
        if duration:
            print("is_command = " + str(VoiceEntry.is_command))
            if VoiceEntry.is_command:
                fmt = fmt + ' [length: {0[0]}:{0[1]}m/{1[0]}:{1[1]}m]'.format(divmod(self.current_position, 60), divmod(duration, 60))
                print("Setting is_command to False")
                VoiceEntry.is_command = False
            else:
                fmt = fmt + ' [length: {0[0]}:{0[1]}m]'.format(divmod(duration, 60))
        return fmt.format(self.player, self.requester)


class VoiceState:
    def __init__(self, bot):
        self.current = None
        self.voice = None
        self.bot = bot
        self.play_next_song = asyncio.Event()
        self.songs = asyncio.Queue()
        self.timer_task = asyncio.Future()
        self.skip_votes = set()  # a set of user_ids that voted
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())

    def is_playing(self):
        if self.voice is None or self.current is None:
            return False

        player = self.current.player
        return not player.is_done()

    @property
    def player(self):
        return self.current.player

    def skip(self):
        self.skip_votes.clear()
        if self.is_playing():
            self.player.stop()

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        while True:
            self.play_next_song.clear()
            self.current = await self.songs.get()
            await self.bot.send_message(self.current.channel, 'Now playing ' + str(self.current))
            self.timer_task = self.bot.loop.create_task(self.current_position_timer())
            self.current.player.start()
            await self.play_next_song.wait()

    async def current_position_timer(self):
        if self.player.is_playing():
            while VoiceEntry.current_position != self.player.duration:
                try:
                    print("Running task with timer")
                    VoiceEntry.current_position += 1
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    print("Task got cancelled. Resetting timer...")
                    VoiceEntry.current_position = 0
                    return
            else:
                VoiceEntry.current_position = 0
                # We need to cancel current task
                self.timer_task.cancel()


class Voice:
    """
    Voice/play Commands
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}
        self.checks = utils.PermissionChecks(bot)
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    # Send message
    async def send(self, msg):
        await self.bot.say(msg)

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)
        if state is None:
            state = VoiceState(self.bot)
            self.voice_states[server.id] = state

        return state

    async def create_voice_client(self, channel):
        voice = await self.bot.join_voice_channel(channel)
        state = self.get_voice_state(channel.server)
        state.voice = voice

    def __unload(self):
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                state.timer_task.cancel()
                if state.voice:
                    self.bot.loop.create_task(state.voice.disconnect())
            except:
                pass

    async def check_capabilities(self, msg, vc):

        if vc is None:
            await self.bot.send_message(msg.channel, "You are not in a voice channel.")
            return False

        if not shutil.which('ffmpeg'):
            await self.bot.send_message(msg.channel, "How am I supposed to speak without codecs!? Install `ffmpeg`!.")
            return False

        bot = msg.server.get_member(self.bot.user.id)
        permissions = vc.permissions_for(bot)

        if not permissions.speak:
            await self.bot.send_message(msg.channel, "Failed to connect to channel. Reason: `muted`")
            return False

        # Looks like checking if muted is enough even if we're lacking permissions or if it's afk channel
        #if not permissions.connect:
        #    await self.bot.send_message(msg.channel, "Failed to connect to channel. Reason: can't connect to this channel.")
        #    return False

        return True

    async def play_sound(self, ctx, snd):

        vc = ctx.message.author.voice_channel

        if not await self.check_capabilities(ctx.message, vc):
            return

        state = self.get_voice_state(ctx.message.server)

        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        try:
            player = state.voice.create_ffmpeg_player('sounds/' + snd + '.mp3')
            player.start()
            while player.is_playing():
                await asyncio.sleep(0.2)
            else:
                await ctx.invoke(self.stop)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))

    # List commands & play command group
    @commands.command(pass_context=True)
    async def sounds(self, ctx):
        """List sounds."""

        cursor = self.bot.db.cursor()

        if not await utils.db_check(self.bot, ctx.message, cursor, "sounds"):
            return

        msg = "`Usage: Kurisu, play <name>`\n```List of sounds:\n"

        cursor.execute("SELECT * FROM sounds")
        data = cursor.fetchall()
        cursor.close()
        for row in data:
            msg += row[0] + "\n"
        msg += "random\n"
        msg += "```"
        await self.send(msg)

    @commands.command(pass_context=True)
    async def play(self, ctx, *, name: str):
        """Plays sound. Usage: Kurisu, play <name>"""

        cursor = self.bot.db.cursor()

        if not await utils.db_check(self.bot, ctx.message, cursor, "sounds"):
            return

        if name == "random":
            cursor.execute("SELECT * FROM sounds")
            data = cursor.fetchall()
            snd = []
            for row in data:
                snd.append(row[0])
            i = randrange(0, len(snd))

            await self.play_sound(ctx, snd[i])
        else:
            cursor.execute("SELECT * FROM sounds WHERE name=?", (name,))
            row = cursor.fetchone()
            snd = row[0]

            await self.play_sound(ctx, snd)

        cursor.close()

    @commands.command(pass_context=True, no_pm=True)
    async def summon(self, ctx):
        """Summons the bot to join your voice channel."""

        if ctx.message.server.id != "132200767799951360":
            if not await self.checks.check_perms(ctx.message, 1):
                return

        vc = ctx.message.author.voice_channel

        if not await self.check_capabilities(ctx.message, vc):
            return False

        state = self.get_voice_state(ctx.message.server)

        if state.voice is None:
            state.voice = await self.bot.join_voice_channel(vc)
        else:
            await state.voice.move_to(vc)

        return True

    @commands.command(pass_context=True, name="play-u")
    async def play_u(self, ctx, *, song: str):
        """Plays youtube video. Usage: Kurisu, play-u <url>"""

        if ctx.message.server.id != "132200767799951360":
            if not await self.checks.check_perms(ctx.message, 1):
                return

        state = self.get_voice_state(ctx.message.server)
        opts = {
            'default_search': 'auto',
            'quiet': True,
        }

        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        try:
            player = await state.voice.create_ytdl_player(song, ytdl_options=opts, after=state.toggle_next)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
        else:
            player.volume = 0.2
            entry = VoiceEntry(ctx.message, player)
            await self.bot.say('Enqueued ' + str(entry))
            await state.songs.put(entry)

    @commands.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        """Stops playing audio and leaves the voice channel.
        This also clears the queue.
        """

        if ctx.message.server.id != "132200767799951360":
            if not await self.checks.check_perms(ctx.message, 1):
                return

        server = ctx.message.server
        state = self.get_voice_state(server)

        if state.is_playing():
            player = state.player
            player.stop()

        try:
            state.audio_player.cancel()
            state.timer_task.cancel()
            del self.voice_states[server.id]
            await state.voice.disconnect()
        except:
            pass

    @commands.command(pass_context=True, no_pm=True)
    async def volume(self, ctx, value: int):
        """Sets the volume of the currently playing song."""

        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.volume = value / 100
            await self.bot.say('Set the volume to {:.0%}'.format(player.volume))

    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        """Vote to skip a song. The song requester can automatically skip.
        """

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        voter = ctx.message.author
        if voter == state.current.requester:
            await self.bot.say('Requester requested skipping song...')
            state.timer_task.cancel()
            state.skip()
        elif voter.id not in state.skip_votes:
            state.skip_votes.add(voter.id)
            total_votes = len(state.skip_votes)

            if total_votes >= 3:
                await self.bot.say('Skip vote passed, skipping song...')
                state.timer_task.cancel()
                state.skip()
            else:
                await self.bot.say('Skip vote added, currently at [{}/3]'.format(total_votes))
        else:
            await self.bot.say('You have already voted to skip this song.')

    @commands.command(pass_context=True, no_pm=True)
    async def playing(self, ctx):
        """Shows info about the currently played song."""

        state = self.get_voice_state(ctx.message.server)
        if state.current is None:
            await self.bot.say('Not playing anything.')
        else:
            VoiceEntry.is_command = True
            print("Setting is_command to True")
            await self.bot.say('Now playing {}'.format(state.current))


def setup(bot):
    bot.add_cog(Voice(bot))
