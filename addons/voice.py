import asyncio
import discord
import shutil
from addons import utils
from discord.ext import commands
from random import randrange, shuffle
from collections import deque

if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    # note that on windows this DLL is automatically provided for you
    discord.opus.load_opus('/usr/lib/libopus.so')


class QueueItem:

    def __init__(self, channel, requester, player, song):
        self.requester = requester
        self.channel = channel
        self.player = player
        self.song = song

    def __str__(self):
        fmt = '*{0.title}* uploaded by {0.uploader} and requested by {1.display_name}'
        if self.player.is_live:
            fmt = fmt + ' [live stream]'
        elif self.player.duration:
            fmt = fmt + ' [length: {0[0]}:{0[1]}m]'.format(divmod(self.player.duration, 60))
        return fmt.format(self.player, self.requester)


class VoiceState:

    def __init__(self, bot, voice_module):
        self.voice_client = None
        self.bot = bot
        self.voice_module = voice_module
        self.skip_votes = set()  # a set of user_ids that voted
        self.queue = deque()
        self.current = {'request': None, 'player': None}
        self.play_next_song = asyncio.Event()
        self.task = None
        self.volume = 0.2
        self.ytdl_opts = {
            'default_search': 'auto',
            'quiet': True,
        }

    def do_skip(self):
        self.skip_votes.clear()
        if self.is_playing():
            self.current['player'].stop()

    async def skip(self, channel, voter):

        if voter == self.current['request'].requester:
            await self.bot.send_message(channel, 'Requester requested skipping song...')
            self.do_skip()
        elif voter.id not in self.skip_votes:
            self.skip_votes.add(voter.id)
            total_votes = len(self.skip_votes)
            votes_to_skip = len(self.voice_client.channel.voice_members) % 2

            if total_votes >= votes_to_skip:
                await self.bot.send_message(channel, 'Skip vote passed, skipping song...')
                self.do_skip()
            else:
                await self.bot.send_message(channel, 'Skip vote added, currently at [{}/{}]'.format(total_votes, votes_to_skip))
        else:
            await self.bot.send_message(channel, 'You have already voted to skip this song.')

    async def play(self, channel, requester, song):
        try:
            player = await self.voice_client.create_ytdl_player(song, ytdl_options=self.ytdl_opts)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(channel, fmt.format(type(e).__name__, e))
        else:
            item = QueueItem(channel, requester, player, song)
            self.queue.append(item)
            self.get_task()
            return item

    def is_playing(self):
        if self.voice_client is None or self.current['player'] is None:
            return False

        player = self.current['player']
        return not player.is_done()

    def stop(self):
        self.get_task().cancel()

        if self.is_playing():
            self.current['player'].stop()

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    def get_task(self):
        if self.task is None:
            self.task = self.bot.loop.create_task(self.audio_player_task())

        return self.task

    def change_volume(self, value):
        if self.is_playing():
            self.volume = value / 100

            player = self.current['player']
            player.volume = self.volume

    async def disconnect(self):
        if self.voice_client is not None:
            await self.voice_client.disconnect()

    async def join_channel(self, vc):
        if self.voice_client is None:
            self.voice_client = await self.bot.join_voice_channel(vc)
        else:
            await self.voice_client.move_to(vc)

    async def audio_player_task(self):
        try:
            while True:
                self.play_next_song.clear()
                self.current['request'] = self.queue.popleft()
                self.current['player'] = await self.voice_client.create_ytdl_player(self.current['request'].song, ytdl_options=self.ytdl_opts, after=self.toggle_next)
                self.current['player'].volume = self.volume
                self.current['player'].start()
                await self.bot.send_message(self.current['request'].channel, 'Now playing ' + str(self.current['request']))
                await self.play_next_song.wait()
                if not self.queue:
                    await self.bot.send_message(self.current['request'].channel, "Queue is empty! Disconnecting...")
                    self.task = None
                    self.voice_module.remove_voice_state(self.current['request'].channel.server)
                    await self.voice_client.disconnect()
                    break
        except asyncio.CancelledError:
            pass


class Voice:
    """
    Voice/play Commands
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}
        self.checks = utils.PermissionChecks(bot)
        if not shutil.which('ffmpeg'):
            raise Exception('FFMPEG is not installed!')
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    # Send message
    async def send(self, msg):
        await self.bot.say(msg)

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)
        if state is None:
            state = VoiceState(self.bot, self)
            self.voice_states[server.id] = state

        return state

    def remove_voice_state(self, server):
        if self.voice_states[server.id]:
            del self.voice_states[server.id]

    def __unload(self):
        for state in self.voice_states.values():
            state.stop()
            if state.voice_client:
                self.bot.loop.create_task(state.voice_client.disconnect())

    async def check_capabilities(self, msg, vc):

        if vc is None:
            await self.bot.send_message(msg.channel, "You are not in a voice channel.")
            return False

        bot = msg.server.get_member(self.bot.user.id)
        permissions = vc.permissions_for(bot)

        if not permissions.speak:
            await self.bot.send_message(msg.channel, "Failed to connect to channel. Reason: `muted`")
            return False

        return True

    @commands.command(pass_context=True, no_pm=True)
    async def summon(self, ctx):
        """Summons the bot to join your voice channel."""

        if ctx.message.server.id != "132200767799951360":
            if not await self.checks.check_perms(ctx.message, 1):
                return False

        vc = ctx.message.author.voice_channel

        if not await self.check_capabilities(ctx.message, vc):
            return False

        state = self.get_voice_state(ctx.message.server)

        await state.join_channel(vc)

        return True

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

    @commands.command(pass_context=True, no_pm=True)
    async def play(self, ctx, *, name: str):
        """Plays sound. Usage: Kurisu, play <name>"""

        cursor = self.bot.db.cursor()

        if not await utils.db_check(self.bot, ctx.message, cursor, "sounds"):
            return

        if name == "random":
            cursor.execute("SELECT * FROM sounds")
            data = cursor.fetchall()
            sounds = []
            for row in data:
                sounds.append(row[0])
            i = randrange(0, len(sounds))
            snd = sounds[i]
        else:
            cursor.execute("SELECT * FROM sounds WHERE name=?", (name,))
            row = cursor.fetchone()
            if not row:
                await self.bot.send_message(ctx.message.channel, "Sound not found!")
                return
            snd = row[0]

        cursor.close()

        state = self.get_voice_state(ctx.message.server)

        if state.is_playing():
            return

        success = await ctx.invoke(self.summon)
        if not success:
            return

        try:
            player = state.voice_client.create_ffmpeg_player('sounds/' + snd + '.mp3')
            state.current['player'] = player
            player.start()
            while player.is_playing():
                await asyncio.sleep(0.2)
            else:
                try:
                    state.current['player'] = None
                    await state.disconnect()
                    self.remove_voice_state(ctx.message.server)
                except:
                    pass
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))

    @commands.command(pass_context=True, name="play-u", no_pm=True)
    async def play_u(self, ctx, *, song: str):
        """Plays youtube video. Usage: Kurisu, play-u <url>"""

        if ctx.message.server.id != "132200767799951360":
            if not await self.checks.check_perms(ctx.message, 1):
                return

        state = self.get_voice_state(ctx.message.server)

        success = await ctx.invoke(self.summon)
        if not success:
            return

        item = await state.play(ctx.message.channel, ctx.message.author, song)
        await self.send('Enqueued ' + str(item))

    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        """Vote to skip a song. The song requester can automatically skip."""

        state = self.get_voice_state(ctx.message.server)

        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        voter = ctx.message.author
        channel = ctx.message.channel

        await state.skip(channel, voter)

    @commands.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        """Stops player and disconnects bot from channel"""

        if ctx.message.server.id != "132200767799951360":
            if not await self.checks.check_perms(ctx.message, 1):
                return

        state = self.get_voice_state(ctx.message.server)

        state.stop()
        await state.disconnect()
        self.remove_voice_state(ctx.message.server)

    @commands.command(pass_context=True, no_pm=True)
    async def volume(self, ctx, value: int):
        """Sets the volume of the currently playing song."""

        state = self.get_voice_state(ctx.message.server)

        if state.current['request'] is None:
            await self.send('Not playing anything.')
            return

        state.change_volume(value)
        await self.bot.say('Set the volume to {}%'.format(value))

    @commands.command(pass_context=True, no_pm=True)
    async def playing(self, ctx):
        """Shows info about the currently played song."""

        state = self.get_voice_state(ctx.message.server)

        if state.current['request'] is None:
            await self.bot.say('Not playing anything.')
            return

        await self.bot.say('Now playing {}'.format(state.current['request']))

    @commands.command(pass_context=True, no_pm=True)
    async def queue(self, ctx):
        """Shows songs queue."""

        state = self.get_voice_state(ctx.message.server)

        if state.current['request'] is None:
            await self.send('Not playing anything.')
            return

        songs_queue = []
        count = 1
        for song in state.queue:
            count += 1
            songs_queue.append("{}. ".format(count) + str(song))
        await self.send("Current queue:\n1. {}\n{}".format(state.current['request'], "\n".join(songs_queue)))

    @commands.command(pass_context=True, no_pm=True)
    async def shuffle(self, ctx):
        """Shuffles songs queue."""

        if ctx.message.server.id != "132200767799951360":
            if not await self.checks.check_perms(ctx.message, 1):
                return

        state = self.get_voice_state(ctx.message.server)

        if state.current['request'] is None:
            await self.send('Not playing anything.')
            return

        if len(state.queue) < 2:
            await self.send('Nothing to shuffle. Add more songs.')
        else:
            shuffle(state.queue)
            await self.send('Queue shuffled!')


def setup(bot):
    bot.add_cog(Voice(bot))
