# main.py
import discord
from discord.ext import commands
import asyncio
import os
import yt_dlp
import aiohttp
from urllib.parse import urlparse
import re

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

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
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class MusicQueue:
    def __init__(self):
        self.queue = []
        self.current = None

    def add_song(self, song):
        self.queue.append(song)

    def next_song(self):
        if self.queue:
            return self.queue.pop(0)
        return None

    def clear(self):
        self.queue.clear()
        self.current = None

music_queues = {}

def get_queue(guild_id):
    if guild_id not in music_queues:
        music_queues[guild_id] = MusicQueue()
    return music_queues[guild_id]

def is_youtube_url(url):
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    return youtube_regex.match(url) is not None

def is_facebook_url(url):
    facebook_regex = re.compile(
        r'(https?://)?(www\.)?(facebook|fb)\.(com|watch)/'
        r'.*/(videos?/|watch/|v/)'
    )
    return facebook_regex.match(url) is not None

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='join')
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f'Joined {channel.name}!')
    else:
        await ctx.send('You need to be in a voice channel first!')

@bot.command(name='leave')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send('Disconnected from voice channel!')
    else:
        await ctx.send('Not connected to a voice channel!')

@bot.command(name='play')
async def play(ctx, *, url_or_search):
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send('You need to be in a voice channel!')
            return

    queue = get_queue(ctx.guild.id)

    try:
        if is_youtube_url(url_or_search) or is_facebook_url(url_or_search):
            await ctx.send(f'Adding to queue: {url_or_search}')
            player = await YTDLSource.from_url(url_or_search, loop=bot.loop, stream=True)
        else:
            search_query = f"ytsearch:{url_or_search}"
            await ctx.send(f'Searching for: {url_or_search}')
            player = await YTDLSource.from_url(search_query, loop=bot.loop, stream=True)

        queue.add_song(player)
        await ctx.send(f'Added to queue: **{player.title}**')

        if not ctx.voice_client.is_playing():
            await play_next(ctx)

    except Exception as e:
        await ctx.send(f'Error playing audio: {str(e)}')

@bot.command(name='file')
async def play_file(ctx):
    if not ctx.message.attachments:
        await ctx.send('Please attach an audio file!')
        return

    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send('You need to be in a voice channel!')
            return

    attachment = ctx.message.attachments[0]
    audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.flac']
    if not any(attachment.filename.lower().endswith(ext) for ext in audio_extensions):
        await ctx.send('Please upload a valid audio file!')
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status == 200:
                    filename = f"temp_{attachment.filename}"
                    with open(filename, 'wb') as f:
                        f.write(await resp.read())

                    source = discord.PCMVolumeTransformer(
                        discord.FFmpegPCMAudio(filename, **ffmpeg_options)
                    )
                    queue = get_queue(ctx.guild.id)
                    queue.add_song(source)
                    await ctx.send(f'Added to queue: **{attachment.filename}**')

                    if not ctx.voice_client.is_playing():
                        await play_next(ctx)

    except Exception as e:
        await ctx.send(f'Error playing file: {str(e)}')

async def play_next(ctx):
    queue = get_queue(ctx.guild.id)

    if ctx.voice_client and queue.queue:
        source = queue.next_song()
        queue.current = source

        def after_playing(error):
            if error:
                print(f'Player error: {error}')
            coro = play_next(ctx)
            fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f'Error in after_playing: {e}')

        ctx.voice_client.play(source, after=after_playing)

        if hasattr(source, 'title'):
            await ctx.send(f'Now playing: **{source.title}**')
        else:
            await ctx.send('Now playing uploaded file')

@bot.command(name='skip')
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send('Skipped current song!')
    else:
        await ctx.send('Nothing is currently playing!')

@bot.command(name='queue')
async def show_queue(ctx):
    queue = get_queue(ctx.guild.id)

    if not queue.queue:
        await ctx.send('Queue is empty!')
        return

    queue_list = []
    for i, song in enumerate(queue.queue[:10], 1):
        if hasattr(song, 'title'):
            queue_list.append(f"{i}. {song.title}")
        else:
            queue_list.append(f"{i}. Uploaded file")

    embed = discord.Embed(title="Music Queue", description="\n".join(queue_list), color=0x00ff00)

    if queue.current:
        if hasattr(queue.current, 'title'):
            embed.add_field(name="Now Playing", value=queue.current.title, inline=False)
        else:
            embed.add_field(name="Now Playing", value="Uploaded file", inline=False)

    await ctx.send(embed=embed)

@bot.command(name='clear')
async def clear_queue(ctx):
    queue = get_queue(ctx.guild.id)
    queue.clear()
    await ctx.send('Queue cleared!')

@bot.command(name='pause')
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send('Paused!')
    else:
        await ctx.send('Nothing is currently playing!')

@bot.command(name='resume')
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send('Resumed!')
    else:
        await ctx.send('Nothing is paused!')

@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client:
        queue = get_queue(ctx.guild.id)
        queue.clear()
        ctx.voice_client.stop()
        await ctx.send('Stopped playing and cleared queue!')
    else:
        await ctx.send('Nothing is currently playing!')

@bot.command(name='volume')
async def volume(ctx, volume: int):
    if ctx.voice_client:
        if 0 <= volume <= 100:
            ctx.voice_client.source.volume = volume / 100
            await ctx.send(f'Volume set to {volume}%')
        else:
            await ctx.send('Volume must be between 0 and 100!')
    else:
        await ctx.send('Not connected to a voice channel!')

@bot.command(name='help_music')
async def help_music(ctx):
    embed = discord.Embed(title="Music Bot Commands", color=0x00ff00)
    embed.add_field(name="!join", value="Join voice channel", inline=False)
    embed.add_field(name="!leave", value="Leave voice channel", inline=False)
    embed.add_field(name="!play <url/search>", value="Play from YouTube/Facebook or search", inline=False)
    embed.add_field(name="!file", value="Play uploaded audio file", inline=False)
    embed.add_field(name="!skip", value="Skip current song", inline=False)
    embed.add_field(name="!queue", value="Show current queue", inline=False)
    embed.add_field(name="!clear", value="Clear queue", inline=False)
    embed.add_field(name="!pause", value="Pause current song", inline=False)
    embed.add_field(name="!resume", value="Resume paused song", inline=False)
    embed.add_field(name="!stop", value="Stop and clear queue", inline=False)
    embed.add_field(name="!volume <0-100>", value="Set volume", inline=False)
    await ctx.send(embed=embed)

if __name__ == '__main__':
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Set DISCORD_TOKEN in Render environment!")
    else:
        bot.run(token)
