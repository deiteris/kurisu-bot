# Kurisu discord bot
A discord chat bot which combines different simple features for entertainment purposes.

# Requirements
<ul>
<li>Python 3+</li>
<li>Latest discord.py library with voice support</li>
<li>FFMPEG and youtube-dl for music and sounds</li>
<li><a href="https://pypi.python.org/pypi/wikipedia/" target="_blank">Wikipedia</a>, <a href="https://pypi.python.org/pypi/wolframalpha/" target="_blank">WolframAlpha</a> and <a href="https://pypi.python.org/pypi/psutil/" target="_blank">psutil</a> python packages
</ul>

# Key features
<ul>
<li>(Almost) flexible access system for commands using roles</li>
<li>Simple, yet, effective mute management (timed and permanent mute)</li>
<li>Music player based on discord.py and youtube-dl capabilities</li>
<li>Switch between bot and user account without any hussle. All bot functions are compatible with user account features.</li>
</ul>

# How to use
<ul>
<li>Check out <b>config.example.json</b>. Fill necessary fields and rename it to <b>config.json</b></li>
<li>Run <b>run.py</b>, use <b>Kurisu, help</b> to check out full list of commands.</li>
<li>Perform first-time initialization for database using <b>Kurisu, db init</b></li>
<li>Discover all features and enjoy!</li>
</ul>

# Defaults
<ul>
<li>4 bot prefixes: <b>'Kurisu, ', "kurisu, ", 'k.', 'K.'</b>.</li>
<li>Owner provided in config has access to all commands.</li>
<li>Database have several Meme entries and Sound entries according to 'sounds' directory</li>
<li>Default access roles are 'commander' (level 3) and 'moderator' (level 2)</li>
</ul>

# Commands access system
The system is pretty simple: the higher level role has, the more commands its owner can access. This means that if role has level 3, its owner can use service, mod and music commands.
<p>Most commands in 'service' addon require at least level 3 or greater.</p>
<p>Commands in 'mod' addon require at least level 2 or greater.</p>
<p>Some music commands in 'voice' addon require at least level 1 or greater (to prevent abuse).</p>
<p>There are some commands in 'service' addon, which can be accessed only by owner or level 9000 or greater which can be considered as co-owner.</p>
