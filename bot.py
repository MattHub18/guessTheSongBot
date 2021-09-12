import os
import random
import pyrebase
import discord
from discord.ext import commands
from discord import FFmpegPCMAudio


class Db:
    def __init__(self):
        firebase_config = {
            'apiKey': os.environ['API_KEY'],
            'authDomain': os.environ['AUTH_DOMAIN'],
            'databaseURL': os.environ['DATABASE_URL'],
            'projectId': os.environ['PROJECT_ID'],
            'storageBucket': os.environ['STORAGE_BUCKET'],
            'messagingSenderId': os.environ['MESSAGING_SENDER_ID'],
            'appId': os.environ['APP_ID']
        }
        firebase = pyrebase.initialize_app(firebase_config)
        database = firebase.database()
        self.song_list = []
        for songs in database.child("songs").get().each():
            self.song_list.append(songs.val())


def next_song():
    if GuessTheSong.instance:
        GuessTheSong.instance.get_random_song()
        GuessTheSong.song_title = GuessTheSong.instance.current_song_title
        GuessTheSong.song_url = GuessTheSong.instance.current_song_url


class GuessTheSong:
    class Game:
        def __init__(self):
            self.db = Db()
            self.song_list = self.db.song_list
            self.current_song_title = None
            self.current_song_url = None

        def get_random_song(self):
            current_song = random.choice(self.song_list)
            self.current_song_title = current_song["title"]
            self.current_song_url = current_song["url"]
            self.song_list.remove(current_song)

    instance = None
    song_title = None
    song_url = None

    def __init__(self):
        if not GuessTheSong.instance:
            GuessTheSong.instance = GuessTheSong.Game()
            next_song()


intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix='>', intents=intents)

match_table = {}


@bot.event
async def on_ready():
    print("Bot is ready!")
    channel = bot.get_channel(int(os.environ['CHANNEL']))
    await channel.send("Welcome to Guess The Song v1.0! Type >guide to get all commands")


@bot.command()
async def guide(ctx):
    em = discord.Embed(title="Guide", description="This is the commands\' list you can use")
    em.add_field(name="Commands:",
                 value=">join => bot joins voice channel\n"
                       ">leave => bot leaves voice channel\n"
                       ">play => play current song\n"
                       ">skip => skip current song\n"
                       ">guess \"title\"  => guess the song, title=insert song title\n"
                       ">table => show the table of current match\n"
                       ">guide => show this guide")

    await ctx.send(embed=em)


@bot.command(pass_context=True)
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.message.author.voice.channel
        await channel.connect()
        await ctx.send("I joined the voice channel")
    else:
        await ctx.send("You must to be in a voice channel to run this command!")


@bot.command(pass_context=True)
async def leave(ctx):
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.send("I left the voice channel")
    else:
        await ctx.send("I am not in a voice channel!")


@bot.command(pass_context=True)
async def play(ctx):
    if ctx.author.voice:
        game = GuessTheSong()
        source = FFmpegPCMAudio(game.song_url)
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        voice.play(source)
    else:
        await ctx.send("You must to be in a voice channel to run this command!")


@bot.command()
async def guess(ctx, message):
    if ctx.author.voice:
        game = GuessTheSong()
        if message.casefold() == game.song_title.casefold():
            author = str(ctx.message.author).split("#")[0]
            await ctx.send("Correct! One point to {author}".format(author=author))
            global match_table
            if author in match_table.keys():
                match_table.update({author: match_table[author] + 1})
            else:
                match_table[author] = 1
            next_song()
        else:
            await ctx.send("Try again!")
    else:
        await ctx.send("You must to be in a voice channel to run this command!")


@bot.command()
async def skip(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    voice.stop()
    await ctx.send("Skipped song")
    next_song()


@bot.command()
async def table(ctx):
    global match_table
    if match_table:
        match_table = dict(sorted(match_table.items(), key=lambda item: item[1]))
        str_name = ""
        for name in match_table.keys():
            str_name += name + "\n"
        str_points = ""
        for points in match_table.values():
            str_points += str(points) + "\n"
        em = discord.Embed(title="Table", description="Today's table:")
        em.add_field(name="Name:",
                     value=str_name)
        em.add_field(name="Points:",
                     value=str_points)

        await ctx.send(embed=em)
    else:
        await ctx.send("Nobody is guessing!")


bot.run(os.environ['TOKEN'])
