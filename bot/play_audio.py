import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
import shutil  # Added to check for FFmpeg

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

loop_enabled = {}  # Track loop state per guild
current_song = {}  # Track current song per guild

# yt-dlp options
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

if os.path.exists('cookies.txt'):
    ytdl_format_options['cookiefile'] = 'cookies.txt'
    print("🍪 YouTube cookies loaded from cookies.txt")

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


async def after_playback(ctx, error):
    """Called after a song finishes playing"""
    if error:
        print(f'Player error: {error}')
        return

    guild_id = ctx.guild.id

    # If loop is enabled, replay the current song
    if loop_enabled.get(guild_id, False) and guild_id in current_song:
        print(f"[v0] Looping song: {current_song[guild_id]['title']}")
        try:
            player = await YTDLSource.from_url(current_song[guild_id]['url'], loop=bot.loop, stream=True)
            ctx.voice_client.play(player,
                                  after=lambda e: asyncio.run_coroutine_threadsafe(after_playback(ctx, e), bot.loop))
        except Exception as e:
            print(f"[v0] Error looping song: {e}")


@bot.event
async def on_ready():
    ffmpeg_path = shutil.which('ffmpeg')
    if not ffmpeg_path:
        print('⚠️  WARNING: FFmpeg not found! Audio will not play.')
        print('📥 Install FFmpeg:')
        print('   Windows: Download from https://ffmpeg.org/download.html')
        print('   Or use: winget install ffmpeg')
        print('   Or use: choco install ffmpeg')
    else:
        print(f'✅ FFmpeg found at: {ffmpeg_path}')

    print(f'✅ Bot is ready! Logged in as {bot.user.name} ({bot.user.id})')
    print(f'🎵 Connected to {len(bot.guilds)} server(s)')
    print('\n📋 Available voice channels:')
    for guild in bot.guilds:
        print(f'  Server: {guild.name}')
        for channel in guild.voice_channels:
            print(f'    - {channel.name} (ID: {channel.id})')
    await bot.change_presence(activity=discord.Game(name="!play <url>"))


@bot.event
async def on_voice_state_update(member, before, after):
    """Auto-join when a user enters a specific voice channel"""

    # Skip if it's the bot itself
    if member.bot:
        return

    # Check if user joined a voice channel
    if after.channel and not before.channel:
        # Auto-join if the channel name is "Click To Preview!"
        if after.channel.name == "Click To Preview!":
            print(f"[v0] User {member.name} joined '{after.channel.name}', attempting to join...")

            # Get the voice client for this guild
            voice_client = discord.utils.get(bot.voice_clients, guild=after.channel.guild)

            if voice_client is None:
                try:
                    await after.channel.connect()
                    print(f"[v0] Successfully connected to '{after.channel.name}'")
                except Exception as e:
                    print(f"[v0] Failed to connect: {e}")
            elif voice_client.channel != after.channel:
                try:
                    await voice_client.move_to(after.channel)
                    print(f"[v0] Moved to '{after.channel.name}'")
                except Exception as e:
                    print(f"[v0] Failed to move: {e}")


@bot.command(name='play', help='Plays audio from YouTube URL')
async def play(ctx, url: str):
    """Play audio from a YouTube URL in your voice channel"""

    if not shutil.which('ffmpeg'):
        await ctx.send("❌ FFmpeg is not installed! Please install FFmpeg to play audio.")
        print("[v0] FFmpeg not found - cannot play audio")
        return

    print(f"[v0] Play command received from {ctx.author.name}")
    print(f"[v0] User voice state: {ctx.author.voice}")

    if not ctx.author.voice:
        await ctx.send("❌ You need to be in a voice channel to use this command!")
        return

    channel = ctx.author.voice.channel
    print(f"[v0] Target channel: {channel.name}")

    if ctx.voice_client is None:
        print(f"[v0] Attempting to connect to {channel.name}...")
        try:
            await channel.connect()
            await ctx.send(f"🔊 Connected to {channel.name}")
            print(f"[v0] Successfully connected!")
        except Exception as e:
            print(f"[v0] Connection failed: {e}")
            await ctx.send(f"❌ Failed to connect: {str(e)}")
            return
    elif ctx.voice_client.channel != channel:
        print(f"[v0] Moving from {ctx.voice_client.channel.name} to {channel.name}...")
        await ctx.voice_client.move_to(channel)
        await ctx.send(f"🔊 Moved to {channel.name}")

    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()

    try:
        await ctx.send(f"⏳ Loading audio from: {url}")
        print(f"[v0] Downloading audio from {url}")

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)

            current_song[ctx.guild.id] = {
                'url': url,
                'title': player.title
            }

            ctx.voice_client.play(player,
                                  after=lambda e: asyncio.run_coroutine_threadsafe(after_playback(ctx, e), bot.loop))

        loop_status = "🔁 (Loop ON)" if loop_enabled.get(ctx.guild.id, False) else ""
        await ctx.send(f"🎵 Now playing: **{player.title}** {loop_status}")
        print(f"[v0] Now playing: {player.title}")

    except Exception as e:
        await ctx.send(f"❌ Error playing audio: {str(e)}")
        print(f"[v0] Error in play command: {e}")


@bot.command(name='loop', help='Toggle looping the current song forever')
async def loop(ctx):
    """Toggle loop mode for the current song"""
    guild_id = ctx.guild.id

    # Toggle loop state
    loop_enabled[guild_id] = not loop_enabled.get(guild_id, False)

    if loop_enabled[guild_id]:
        await ctx.send("🔁 Loop enabled! The current song will play forever.")
        print(f"[v0] Loop enabled for guild {guild_id}")
    else:
        await ctx.send("🔁 Loop disabled!")
        print(f"[v0] Loop disabled for guild {guild_id}")


@bot.command(name='join', help='Manually join your voice channel')
async def join(ctx):
    """Manually join the voice channel you're in"""

    if not ctx.author.voice:
        await ctx.send("❌ You need to be in a voice channel first!")
        return

    channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await channel.connect()
        await ctx.send(f"🔊 Joined {channel.name}")
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)
        await ctx.send(f"🔊 Moved to {channel.name}")
    else:
        await ctx.send(f"✅ Already in {channel.name}")


@bot.command(name='stop', help='Stops playback and disconnects the bot')
async def stop(ctx):
    """Stop playback and disconnect from voice channel"""

    if ctx.voice_client:
        loop_enabled[ctx.guild.id] = False
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Stopped playback and disconnected")
    else:
        await ctx.send("❌ Bot is not connected to a voice channel")


@bot.command(name='pause', help='Pauses the current playback')
async def pause(ctx):
    """Pause the current playback"""

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Paused playback")
    else:
        await ctx.send("❌ Nothing is playing")


@bot.command(name='resume', help='Resumes paused playback')
async def resume(ctx):
    """Resume paused playback"""

    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed playback")
    else:
        await ctx.send("❌ Playback is not paused")


@bot.command(name='volume', help='Changes the volume (0-100)')
async def volume(ctx, vol: int):
    """Change the volume of the player"""

    if not ctx.voice_client:
        await ctx.send("❌ Bot is not connected to a voice channel")
        return

    if not 0 <= vol <= 100:
        await ctx.send("❌ Volume must be between 0 and 100")
        return

    ctx.voice_client.source.volume = vol / 100
    await ctx.send(f"🔊 Volume set to {vol}%")


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required argument. Use !help <command> for more info")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Use !help to see available commands")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")
        print(f"Error: {error}")


# Main execution
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')

    if not token:
        print("❌ Error: DISCORD_BOT_TOKEN not found in environment variables")
        print("📝 Create a .env file with your Discord bot token")
        exit(1)

    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ Failed to login. Check your DISCORD_BOT_TOKEN")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
