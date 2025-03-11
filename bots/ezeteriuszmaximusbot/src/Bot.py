import discord
from discord.ext import commands, tasks
from itertools import cycle
from discord.utils import get
import random
import asyncio
import os
import json
from gtts import gTTS
from random import randint
from discord import Member
from discord.ext.commands import has_permissions, MissingPermissions
import datetime
import random
import ftplib

# Set working directory to one level up from where bot.py is
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(script_dir, "..")
os.chdir(parent_dir)  # Change working directory

print("Working directory set to:", os.getcwd())

global ppv
intents = discord.Intents.all()
client = commands.Bot(command_prefix='maximus!',intents=intents)
status = cycle(['Proszę państwa.','Dziadostwo jak zwykle buszuje.','Gówniarze nie śpią i blokują linie.'])
czybylojuzlinia = 0

@client.event
async def on_ready():
    change_status.start()
    print('EzeteriuszMaximusBOT aktywowany!')
    print(str(datetime.datetime.now().time()))

@tasks.loop(seconds=3)
async def change_status():
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=next(status)))


@client.command()
async def ping(ctx):
    await ctx.send('Proszę państwa. Dziadostwo jak zwykle buszuje. Gówniarze nie śpią i blokują linie.')


@client.command()
async def zgolbrode(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="bezbrody.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="bezbrody.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.event
async def on_message(message):
    member = message.author
    messageContent1 = message.content.lower()
    messageContent = messageContent1.replace(' ', '')
    channelh = client.get_channel(827293597283647568)
    channelog = client.get_channel(637696693663563795)
    if 'zgoliszbrod' in messageContent:
        channel = message.author.voice.channel
        voice = get(client.voice_clients, guild=message.guild)
        if voice and voice.is_connected():
            await voice.move_to(channel)
            voice.play(discord.FFmpegPCMAudio( source="bezbrody.mp3"))
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            await voice.disconnect()
            print('wychodze!!!')
        else:

            voice = await channel.connect()
            voice.play(discord.FFmpegPCMAudio( source="bezbrody.mp3"))
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            await voice.disconnect()
            print('wychodze!!!')
    if 'hujciwdupe' in messageContent:
        channel = message.author.voice.channel
        voice = get(client.voice_clients, guild=message.guild)
        if voice and voice.is_connected():
            await voice.move_to(channel)
            voice.play(discord.FFmpegPCMAudio( source="spadajszczawiu.mp3"))
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            await voice.disconnect()
            print('wychodze!!!')
        else:

            voice = await channel.connect()
            voice.play(discord.FFmpegPCMAudio( source="spadajszczawiu.mp3"))
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            await voice.disconnect()
            print('wychodze!!!')
    if 'tywariacie' in messageContent:
        channel = message.author.voice.channel
        voice = get(client.voice_clients, guild=message.guild)
        if voice and voice.is_connected():
            await voice.move_to(channel)
            voice.play(discord.FFmpegPCMAudio( source="nojakisduren.mp3"))
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            await voice.disconnect()
            print('wychodze!!!')
        else:

            voice = await channel.connect()
            voice.play(discord.FFmpegPCMAudio( source="nojakisduren.mp3"))
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            await voice.disconnect()
            print('wychodze!!!')
    if 'brodeztegoryja' in messageContent or 'brodęztegoryja' in messageContent:
        channel = message.author.voice.channel
        voice = get(client.voice_clients, guild=message.guild)
        if voice and voice.is_connected():
            await voice.move_to(channel)
            voice.play(discord.FFmpegPCMAudio( source="typacanie.mp3"))
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            await voice.disconnect()
            print('wychodze!!!')
        else:

            voice = await channel.connect()
            voice.play(discord.FFmpegPCMAudio( source="typacanie.mp3"))
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            await voice.disconnect()
            print('wychodze!!!')
    if 'kiedytymikurwachuju' in messageContent or 'kiedytymikurwahuju' in messageContent:
        channel = message.author.voice.channel
        voice = get(client.voice_clients, guild=message.guild)
        if voice and voice.is_connected():
            await voice.move_to(channel)
            voice.play(discord.FFmpegPCMAudio( source="tygnoju.mp3"))
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            await voice.disconnect()
            print('wychodze!!!')
        else:

            voice = await channel.connect()
            voice.play(discord.FFmpegPCMAudio( source="tygnoju.mp3"))
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            await voice.disconnect()
            print('wychodze!!!')
    await client.process_commands(message)


@client.event
async def on_voice_state_update(member, before, after):
    czas = str(datetime.datetime.now().time())
    godzina = czas[:2]
    godzinaval = int(godzina)
    print(godzina)
    if after.channel == before.channel:
        return
    if member.bot == True:
        return
    if after is not None and godzinaval > 19:
      channel = after.channel
      voice = get(client.voice_clients, guild=member.guild)
      if voice and voice.is_connected():
          await voice.move_to(channel)
          voice.play(discord.FFmpegPCMAudio( source="niespia.mp3"))
          while voice.is_playing():
              print('gra')
              await asyncio.sleep(2)
          await voice.disconnect()
          print('wychodze!!!')
      else:
          voice = await channel.connect()
          voice.play(discord.FFmpegPCMAudio( source="niespia.mp3"))
          while voice.is_playing():
              print('gra')
              await asyncio.sleep(2)
          await voice.disconnect()
          print('wychodze!!!')


@client.command()
async def telefon(ctx, *, message=None):
    embed = discord.Embed(title="Tajemnice Losu - Telefon", description='Zaraz dołącze na twój kanał!', colour=discord.Color.blue())
    embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
    message4 = await ctx.send(embed=embed)
    await ctx.message.delete()

    questions = [
        f"Imię?"
    ]
    answers = []

    def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

    for i in questions:
            channel = ctx.message.author.voice.channel
            voice = get(client.voice_clients, guild=ctx.guild)
            if voice and voice.is_connected():

                await voice.move_to(channel)
                voice.play(discord.FFmpegPCMAudio( source="dziendobry1.mp3"))
                while voice.is_playing():
                    print('gra')
                    await asyncio.sleep(1)
                print('wychodze!!!')
            else:

                voice = await channel.connect()
                voice.play(discord.FFmpegPCMAudio( source="dziendobry1.mp3"))
                while voice.is_playing():
                    print('gra')
                    await asyncio.sleep(0.5)
                print('wychodze!!!')

            try:
                  voice.play(discord.FFmpegPCMAudio( source="tajemnicelosusoundtrack.mp3"))
                  msg = await client.wait_for('message', timeout=60.0, check=check)


            except asyncio.TimeoutError:
                    await ctx.send("Od nowa tylko szybciej zateguj!")
                    await voice.disconnect()
                    return
            else:
                    answers.append(msg.content)
                    voice.stop()
                    for i in answers:
                        print(str(i))
                        messageContent1 = str(i).lower()
                        messageContent = str(i).replace(' ', '')
                        if 'zgoliszbrod' in messageContent:
                            voice.play(discord.FFmpegPCMAudio( source="bezbrody.mp3"))
                            while voice.is_playing():
                                print('gra')
                                await asyncio.sleep(2)
                            questions = []
                            await voice.disconnect()
                            print('wychodze!!!')
                            break
                        if 'hujciwdupe' in messageContent:
                            voice.play(discord.FFmpegPCMAudio( source="spadajszczawiu.mp3"))
                            while voice.is_playing():
                                print('gra')
                                await asyncio.sleep(2)
                            questions = []
                            await voice.disconnect()
                            print('wychodze!!!')
                            break
                        if 'tywariacie' in messageContent:
                            voice.play(discord.FFmpegPCMAudio( source="nojakisduren.mp3"))
                            while voice.is_playing():
                                print('gra')
                                await asyncio.sleep(2)
                            questions = []
                            await voice.disconnect()
                            print('wychodze!!!')
                            break
                        if 'brodeztegoryja' in messageContent or 'brodęztegoryja' in messageContent:
                            voice.play(discord.FFmpegPCMAudio( source="typacanie.mp3"))
                            while voice.is_playing():
                                print('gra')
                                await asyncio.sleep(2)
                            questions = []
                            await voice.disconnect()
                            print('wychodze!!!')
                            break
                        if 'kiedytymikurwachuju' in messageContent or 'kiedytymikurwahuju' in messageContent:
                            voice.play(discord.FFmpegPCMAudio( source="tygnoju.mp3"))
                            while voice.is_playing():
                                print('gra')
                                await asyncio.sleep(2)
                            questions = []
                            await voice.disconnect()
                            print('wychodze!!!')
                            break


    print(answers)
    for i in questions:
            channel = ctx.message.author.voice.channel
            voice = get(client.voice_clients, guild=ctx.guild)
            if voice and voice.is_connected():

                await voice.move_to(channel)
                voice.play(discord.FFmpegPCMAudio( source="jakie pytanie1.mp3"))
                while voice.is_playing():
                    print('gra')
                    await asyncio.sleep(1)
                print('wychodze!!!')
            else:

                voice = await channel.connect()
                voice.play(discord.FFmpegPCMAudio( source="jakie pytanie1.mp3"))
                while voice.is_playing():
                    print('gra')
                    await asyncio.sleep(0.5)
                print('wychodze!!!')

            try:
                  voice.play(discord.FFmpegPCMAudio( source="tajemnicelosusoundtrack.mp3"))
                  msg = await client.wait_for('message', timeout=60.0, check=check)


            except asyncio.TimeoutError:
                    await ctx.send("Od nowa tylko szybciej zateguj!")
                    await voice.disconnect()
                    return
            else:
                    answers.append(msg.content)
                    voice.stop()


    print(answers)





client.run(os.environ['EZETERIUSZ_TOKEN'])
