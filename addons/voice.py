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


class Song:

    def __init__(self, title, requester, url, uploader, is_live, duration):
        self.title = title
        self.url = url
        self.uploader = uploader
        self.is_live = is_live
        self.duration = duration
        self.requester = requester
        self.current_position = 0
        self.task = None

    def __str__(self):
        fmt = '*{0}* uploaded by {1} and requested by {2.display_name}'
        if self.is_live:
            fmt = fmt + ' [live stream]'
        elif self.duration:
            fmt = fmt + ' [length: {0[0]}:{0[1]}m/{1[0]}:{1[1]}m]'.format(divmod(self.duration, 60), divmod(self.current_position, 60))
        return fmt.format(self.title, self.uploader, self.requester)

    def start_counter(self):
        self.task = asyncio.get_event_loop().create_task(self.current_position_timer())

    def stop_counter(self):
        self.task.cancel()

    async def current_position_timer(self):
        try:
            while self.current_position <= self.duration:
                self.current_position += 1
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass


class QueueItem:

    def __init__(self, channel, song):
        self.channel = channel
        self.song = song
        self.player = None


class VoiceState:

    def __init__(self, bot, voice_module):
        self.voice_client = None
        self.bot = bot
        # Voice_module is Voice object.
        # Used for voice state removal.
        self.voice_module = voice_module
        self.skip_votes = set()  # a set of user_ids that voted
        self.queue = deque()
        self.current = None
        self.current_sound = None
        self.play_next_song = asyncio.Event()
        self.task = None
        self.volume = 0.2

    def do_skip(self):
        self.skip_votes.clear()
        if self.is_playing():
            self.current.player.stop()
            self.current.song.stop_counter()

    async def skip(self, channel, voter):

        if voter == self.current.song.requester:
            await self.bot.send_message(channel, 'Requester requested skipping song...')
            self.do_skip()
        elif voter.id not in self.skip_votes:
            self.skip_votes.add(voter.id)
            total_votes = len(self.skip_votes)
            votes_to_skip = len(self.voice_client.channel.voice_members) % 2

            # Votes to skip = halved amount of members in voice channel, i.e. 50% of votes are needed to skip.
            if total_votes >= votes_to_skip:
                await self.bot.send_message(channel, 'Skip vote passed, skipping song...')
                self.do_skip()
            else:
                await self.bot.send_message(channel, 'Skip vote added, currently at [{}/{}]'.format(total_votes, votes_to_skip))
        else:
            await self.bot.send_message(channel, 'You have already voted to skip this song.')

    async def play(self, channel, requester, song):
        try:
            ytdl_meta_opts = {
                'default_search': 'auto',
                # Probably should lower memory consumption.
                # https://github.com/rg3/youtube-dl/blob/master/youtube_dl/YoutubeDL.py#L158
                'simulate': True,
                'quiet': True,
            }
            player = await self.voice_client.create_ytdl_player(song, ytdl_options=ytdl_meta_opts)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(channel, fmt.format(type(e).__name__, e))
        else:
            # NOTE: Workaround for weird youtube-dl (or discord.py) bug.
            # We put song in QueueItem, so we can create new player in audio_player_task().
            # Here we create and put player only to extract and use metadata.
            # FIXME: FFMPEG just don't want to go if player was loaded, but wasn't used =\
            player.start()
            player.stop()

            song = Song(player.title, requester, player.url, player.uploader, player.is_live, player.duration)
            item = QueueItem(channel, song)
            self.queue.append(item)
            self.get_task()
            return song

    def is_playing(self):
        if self.voice_client is None or self.current.player is None:
            return False

        player = self.current.player
        return not player.is_done()

    def stop(self):
        self.get_task().cancel()

        if self.is_playing():
            # No need to cancel current_position_timer if we aren't playing anything.
            self.current.song.stop_counter()
            self.current.player.stop()

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    def get_task(self):
        if self.task is None:
            self.task = self.bot.loop.create_task(self.audio_player_task())

        return self.task

    def change_volume(self, value):
        if self.is_playing():
            self.volume = value / 100

            player = self.current.player
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
        ytdl_opts = {
            'default_search': 'auto',
            'quiet': True,
        }
        try:
            while True:

                self.play_next_song.clear()
                self.current = self.queue.popleft()

                # NOTE: Workaround for weird youtube-dl (or discord.py) bug.
                # If our queue has more than 3-4 entries, there's a possibility,
                # that entries after 2nd or 3rd entry will be invalidated and skipped.
                # 2x ffmpeg tasks and more memory consumption, but seems to be working stable.
                self.current.player = await self.voice_client.create_ytdl_player(self.current.song.url, ytdl_options=ytdl_opts, after=self.toggle_next)
                self.current.player.volume = self.volume

                # We don't need to activate timer if it's a live stream
                if not self.current.player.is_live:
                    # Create QueueItem.current_position_timer task and put it in QueueItem.task
                    self.current.song.start_counter()

                self.current.player.start()
                await self.bot.send_message(self.current.channel, 'Now playing ' + str(self.current.song))

                await self.play_next_song.wait()

                if not self.queue:
                    await self.bot.send_message(self.current.channel, "Queue is empty! Disconnecting...")
                    self.voice_module.remove_voice_state(self.current.channel.server)
                    await self.disconnect()
                    break

        except asyncio.CancelledError:
            self.voice_module.remove_voice_state(self.current.channel.server)
            await self.disconnect()
            await self.bot.send_message(self.current.channel, "Player stopped.")


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
            self.bot.loop.create_task(state.disconnect())

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
        """Plays local sound. Usage: Kurisu, play <name>"""

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

        if state.is_playing() or state.current_sound:
            return

        success = await ctx.invoke(self.summon)
        if not success:
            return

        try:
            player = state.voice_client.create_ffmpeg_player('sounds/' + snd + '.mp3')
            state.current_sound = player
            player.start()
            while player.is_playing():
                await asyncio.sleep(0.2)
            else:
                try:
                    await state.disconnect()
                    self.remove_voice_state(ctx.message.server)
                except:
                    pass
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))

        state.current_sound = None

    @commands.command(pass_context=True, name="play-u", no_pm=True)
    async def play_u(self, ctx, *, song: str):
        """Plays youtube video. Usage: Kurisu, play-u <url>"""

        if ctx.message.server.id != "132200767799951360":
            if not await self.checks.check_perms(ctx.message, 1):
                return

        state = self.get_voice_state(ctx.message.server)

        if state.current_sound is not None:
            return

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

    @commands.command(pass_context=True, no_pm=True)
    async def volume(self, ctx, value: int):
        """Sets the volume of the currently playing song."""

        state = self.get_voice_state(ctx.message.server)

        if state.current is None:
            await self.send('Not playing anything.')
            return

        state.change_volume(value)
        await self.bot.say('Set the volume to {}%'.format(value))

    @commands.command(pass_context=True, no_pm=True)
    async def playing(self, ctx):
        """Shows info about the currently played song."""

        state = self.get_voice_state(ctx.message.server)

        if state.current is None:
            await self.bot.say('Not playing anything.')
            return

        await self.bot.say('Now playing {}'.format(state.current.song))

    @commands.command(pass_context=True, no_pm=True)
    async def queue(self, ctx):
        """Shows songs queue."""

        state = self.get_voice_state(ctx.message.server)

        if state.current is None:
            await self.send('Not playing anything.')
            return

        songs_queue = []
        count = 1
        for song in state.queue:
            count += 1
            songs_queue.append("{}. ".format(count) + str(song))
        await self.send("Current queue:\n1. {}\n{}".format(state.current.song, "\n".join(songs_queue)))

    @commands.command(pass_context=True, no_pm=True)
    async def shuffle(self, ctx):
        """Shuffles songs queue."""

        if ctx.message.server.id != "132200767799951360":
            if not await self.checks.check_perms(ctx.message, 1):
                return

        state = self.get_voice_state(ctx.message.server)

        if state.current is None:
            await self.send('Not playing anything.')
            return

        if len(state.queue) < 2:
            await self.send('Nothing to shuffle. Add more songs.')
        else:
            shuffle(state.queue)
            await self.send('Queue shuffled!')


def setup(bot):
    bot.add_cog(Voice(bot))
