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
import yt_dlp
# Set working directory to one level up from where bot.py is
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(script_dir, "..")
os.chdir(parent_dir)  # Change working directory

print("Working directory set to:", os.getcwd())

FFMPEG_OPTIONS = {
        'before_options':
        '-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 200M',
        'options': '-vn'
    }

FFMPEG_OPTIONS2 = {'options': '-vn'}

ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'song',  # Filename of the saved mp3 file
    }

creditsocialimages = ['https://i.ytimg.com/vi/pq-koFphG0k/maxresdefault.jpg','https://i.ytimg.com/vi/1PIMW8pryOs/maxresdefault.jpg','https://video-images.vice.com/articles/61713cd171b09a0094c168dd/lede/1635139741537-img7084.jpeg','https://i.ytimg.com/vi/ZBDRIy4X2sU/maxresdefault.jpg','https://preview.redd.it/acd8kg6rxik71.png?auto=webp&s=d429c8ee33e08afe49b073f367de5cd7ca0ec98a','https://i.ytimg.com/vi/UNeDsyT3678/mqdefault.jpg','https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQPkwjo879dY0XoTq7FdHM8oLDphcJcNihduA&usqp=CAU']
creditplusimages = ['https://c.tenor.com/RvBPEdvCqHkAAAAd/social-credit.gif','https://c.tenor.com/LhFDiiL3dxwAAAAC/social-credit-sad-spongebob.gif','https://c.tenor.com/9r1rE1-uyFYAAAAd/social-credit.gif', 'https://c.tenor.com/tZP-9U_E1JAAAAAC/china-credit-score-credit.gif','https://starecat.com/content/wp-content/uploads/xi-jinping-bro-you-just-posted-cringe-you-are-going-to-lose-social-credit-points.jpg','https://i.ytimg.com/vi/0JRd1Fsgavw/maxresdefault.jpg']
nagrodamessage = ['Wykopałeś kartofle','Niestety wykopałeś gufno','Wykopałeś mózg <@290179026474106881>. Troche mały!','Gratulacje! Wykopałeś Prisoners Life 2!','Niestety wykopałeś anime','Gratulacje! Wykopałeś przejebane 200zł wiśniewskiego!','Niestety wykopałeś kartkówke z matmy miodka','Gratulacje! Wykopałeś komputer <@290179026474106881>!','Niestety wykopałeś dziwny post z czerepalni!','Gratulacje! Wykopałeś ukradzione konto fortnite czerepaka!','Niestety wykopałeś skina za 40gr!','Gratulacje! Wykopałeś MidasFisha!','Niestety wykopałeś zużyty złoty kod z keydropa!','Niestety wykopałeś dugana 0/10','Gratulacje! wykopałeś 20%z napadu!','Gratulacje! wykopałeś 20%z napadu!','Niestety wykopałeś obrazy! Rolluj dalej!','Gratulacje wykopałeś czerepaka z plebani!']
kod2 = None
czywygrana = None
kod = None
kod3 = None
quizmembers = None
wagarymembers = []
randomkick = None
damianvalue = None
order66val = 0
sprawdzanie = 0
godzinapol = 0
czyktoswpisaldamian = None
namepoprawny = 0
nameval = None
kodpoprawnygodz = 0
intents = discord.Intents.all()
intents.members = True
intents.voice_states = True
client = commands.Bot(command_prefix='cody!',intents=intents)
status = cycle(['Damian','to','jebany','debil'])
ytdl = yt_dlp.YoutubeDL(ydl_opts)
@client.event
async def on_ready():
    change_status.start()
    print('Pszczelarz aktywowany!')
    print(str(datetime.datetime.now().time()))

@client.command()
async def ping(ctx):
    await ctx.send('Chwała Imperatorowi')

@tasks.loop(seconds=3)
async def change_status():
    await client.change_presence(activity=discord.Game(next(status)))









@client.command()
async def leave(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    voice.stop()
    await asyncio.sleep(2)
    voice.play(discord.FFmpegPCMAudio( source="adiosleave.mp3"))
    print('gram leave')
    while voice.is_playing():
        await asyncio.sleep(4)
        print('gra')
    await ctx.voice_client.disconnect()
    print('wychodze!')



@client.command()
async def miodzix(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    ktoramuzyka = randint(1, 21)
    print(ktoramuzyka)
    if voice and voice.is_connected():
        await voice.move_to(channel)
        if ktoramuzyka == 1:
            voice.play(discord.FFmpegPCMAudio( source="quizmusic.mp3"))
            print('gram You')
        if ktoramuzyka == 2:
            voice.play(discord.FFmpegPCMAudio( source="quizmusic2.mp3"))
            print('gram Mystery')
        if ktoramuzyka == 3:
            voice.play(discord.FFmpegPCMAudio( source="quizmusic3.mp3"))
            print('gram Nowe spoko jest')
        if ktoramuzyka == 4:
            voice.play(discord.FFmpegPCMAudio( source="quizmusic4.mp3"))
            print('gram Home trap intro')
        if ktoramuzyka == 5:
            voice.play(discord.FFmpegPCMAudio( source="na-wieczor.mp3"))
            print('gram na wieczor')
        if ktoramuzyka == 6:
            voice.play(discord.FFmpegPCMAudio( source="quizmusic5.mp3"))
            print('gram Naughty Boy - La la la ft. Sam Smith')
        if ktoramuzyka == 7:
            voice.play(discord.FFmpegPCMAudio( source="quizmusic6.mp3"))
            print('gram We are alive')
        if ktoramuzyka == 8:
            voice.play(discord.FFmpegPCMAudio( source="chill3.mp3"))
            print('gram chill 3')
        if ktoramuzyka == 9:
            voice.play(discord.FFmpegPCMAudio( source="chill_2-dokurno.mp3"))
            print('gram chill 2 dokurno')
        if ktoramuzyka == 10:
            voice.play(discord.FFmpegPCMAudio( source="xddd.mp3"))
            print('gram xddd')
        if ktoramuzyka == 11:
            voice.play(discord.FFmpegPCMAudio( source="maxchill.mp3"))
            print('gram max chill')
        if ktoramuzyka == 12:
            voice.play(discord.FFmpegPCMAudio( source="najlepszy-projekt-demo1.mp3"))
            print('gram najlepszy projekt demo')
        if ktoramuzyka == 13:
            voice.play(discord.FFmpegPCMAudio( source="Projectdemo.mp3"))
            print('gram Project DEMO')
        if ktoramuzyka == 14:
            voice.play(discord.FFmpegPCMAudio( source="nastrojowe.mp3"))
            print('gram nastrojowe')
        if ktoramuzyka == 15:
            voice.play(discord.FFmpegPCMAudio( source="cosnowego.mp3"))
            print('gram cos nowego')
        if ktoramuzyka == 16:
            voice.play(discord.FFmpegPCMAudio( source="MIODZIX_PROJECT.mp3"))
            print('gram MIODZIX_PROJECT')
        if ktoramuzyka == 17:
            voice.play(discord.FFmpegPCMAudio( source="Intoyou.mp3"))
            print('gram Into you ft Ariana Grande')
        if ktoramuzyka == 18:
            voice.play(discord.FFmpegPCMAudio( source="DJJ.mp3"))
            print('gram DJJ')
        if ktoramuzyka == 19:
            voice.play(discord.FFmpegPCMAudio( source="Dziwne.mp3"))
            print('gram Dzwine')
        if ktoramuzyka == 20:
            voice.play(discord.FFmpegPCMAudio( source="Omg.mp3"))
            print('gram OMG')
        if ktoramuzyka == 21:
            voice.play(discord.FFmpegPCMAudio( source="NowyPakietcut.mp3"))
            print('gram nowy pakiet')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        await voice.disconnect()
        print('wychodze')
    else:
        voice = await channel.connect()
        if ktoramuzyka == 1:
            voice.play(discord.FFmpegPCMAudio( source="quizmusic.mp3"))
            print('gram You')
        if ktoramuzyka == 2:
            voice.play(discord.FFmpegPCMAudio( source="quizmusic2.mp3"))
            print('gram Mystery')
        if ktoramuzyka == 3:
            voice.play(discord.FFmpegPCMAudio( source="quizmusic3.mp3"))
            print('gram Nowe spoko jest')
        if ktoramuzyka == 4:
            voice.play(discord.FFmpegPCMAudio( source="quizmusic4.mp3"))
            print('gram Home trap intro')
        if ktoramuzyka == 5:
            voice.play(discord.FFmpegPCMAudio( source="na-wieczor.mp3"))
            print('gram na wieczor')
        if ktoramuzyka == 6:
            voice.play(discord.FFmpegPCMAudio( source="quizmusic5.mp3"))
            print('gram Naughty Boy - La la la ft. Sam Smith')
        if ktoramuzyka == 7:
            voice.play(discord.FFmpegPCMAudio( source="quizmusic6.mp3"))
            print('gram We are alive')
        if ktoramuzyka == 8:
            voice.play(discord.FFmpegPCMAudio( source="chill3.mp3"))
            print('gram chill 3')
        if ktoramuzyka == 9:
            voice.play(discord.FFmpegPCMAudio( source="chill_2-dokurno.mp3"))
            print('gram chill 2 dokurno')
        if ktoramuzyka == 10:
            voice.play(discord.FFmpegPCMAudio( source="xddd.mp3"))
            print('gram xddd')
        if ktoramuzyka == 11:
            voice.play(discord.FFmpegPCMAudio( source="maxchill.mp3"))
            print('gram max chill')
        if ktoramuzyka == 12:
            voice.play(discord.FFmpegPCMAudio( source="najlepszy-projekt-demo1.mp3"))
            print('gram najlepszy projekt demo')
        if ktoramuzyka == 13:
            voice.play(discord.FFmpegPCMAudio( source="Projectdemo.mp3"))
            print('gram Project DEMO')
        if ktoramuzyka == 14:
            voice.play(discord.FFmpegPCMAudio( source="nastrojowe.mp3"))
            print('gram nastrojowe')
        if ktoramuzyka == 15:
            voice.play(discord.FFmpegPCMAudio( source="cosnowego.mp3"))
            print('gram cos nowego')
        if ktoramuzyka == 16:
            voice.play(discord.FFmpegPCMAudio( source="MIODZIX_PROJECT.mp3"))
            print('gram MIODZIX_PROJECT')
        if ktoramuzyka == 17:
            voice.play(discord.FFmpegPCMAudio( source="Intoyou.mp3"))
            print('gram Into you ft Ariana Grande')
        if ktoramuzyka == 18:
            voice.play(discord.FFmpegPCMAudio( source="DJJ.mp3"))
            print('gram DJJ')
        if ktoramuzyka == 19:
            voice.play(discord.FFmpegPCMAudio( source="Dziwne.mp3"))
            print('gram Dzwine')
        if ktoramuzyka == 20:
            voice.play(discord.FFmpegPCMAudio( source="Omg.mp3"))
            print('gram OMG')
        if ktoramuzyka == 21:
            voice.play(discord.FFmpegPCMAudio( source="NowyPakietcut.mp3"))
            print('gram nowy pakiet')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        await voice.disconnect()
        print('wychodze')




@client.command()
async def bajojajo(ctx):
    channel = ctx.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()

    voice.play(discord.FFmpegPCMAudio(source="jajo.mp3"))
    print('Gram bajo jajo')

    # Wait for the audio to finish playing
    while voice.is_playing():
        await asyncio.sleep(1)

    await voice.disconnect()
    print('Wychodze!!!!!')

@client.event
async def on_member_update(before, after):
    if str(after.status) == "offline":
        print("{} has gone {}.".format(after.name,after.status))


@client.command()
async def jacidambajojajo(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="ty_pojebie.mp3"))
        print('Gram ty pojebie')
        await asyncio.sleep(6)
        await voice.disconnect()
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="ty_pojebie.mp3"))
        print('Gram ty pojebie')
        await asyncio.sleep(6)
        await voice.disconnect()

@client.command()
async def order66(ctx, member: discord.Member):
    channel = member.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await ctx.message.delete()
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="order66.mp3"))
        print('ORDER66')
        await asyncio.sleep(13)
        await member.edit(voice_channel= None)
        await voice.disconnect()
    else:
        await ctx.message.delete()
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="order66.mp3"))
        print('ORDER66')
        await asyncio.sleep(13)
        await member.edit(voice_channel= None)
        await voice.disconnect()


@client.command()
async def earrape(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="alien.mp3"))
        print('Gram ty pojebie')
        await asyncio.sleep(60)
        await voice.disconnect()
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="alien.mp3"))
        print('Gram ty pojebie')
        await asyncio.sleep(60)
        await voice.disconnect()

@client.command()
async def starboy(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="Starboy.mp3"))
        print('Gram ty pojebie')
        await asyncio.sleep(239)
        await voice.disconnect()
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="Starboy.mp3"))
        print('Gram ty pojebie')
        await asyncio.sleep(239)
        await voice.disconnect()



@client.command()
async def głowica(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.stop()
        await asyncio.sleep(0.1)
        voice.play(discord.FFmpegPCMAudio( source="dcancel.mp3"))
        print('Anulowano wysadzenie!')
        await asyncio.sleep(4)
        await voice.disconnect()
        return
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="glowica.mp3"))
        print('Wysadzam!')
        await asyncio.sleep(114)
        await voice.channel.delete()
        await voice.disconnect()

@client.event
async def on_voice_state_update(member, before, after):
 global godzinapol
 global sprawdzanie
 global namepoprawny
 global nameval
 global kodpoprawnygodz
 await asyncio.sleep(1)
 print(str(before.channel))
 print(str(after.channel))
 if after.channel == before.channel:
     return
 rolewjatek = discord.utils.get(member.guild.roles, name="Wyjatekgodzpol👮")
 if after is not None and godzinapol == 1 and sprawdzanie == 0 and not member.id == 956911948291784754 and not member.id == 264079253757231104  and not member.id == 212988300137463809 and not rolewjatek in member.roles and not member.bot == True:
  await asyncio.sleep(2)
  print(str(member.display_name))
  channel = after.channel
  await asyncio.sleep(1)
  print(str(channel.name))
  global currentmember
  global kod3
  global quizmembers
  global czywygrana
  ktoramuzyka = 1
  sprawdzanie = 1
  value = randint(0, 10)
  value2 = randint(0, 10)
  value3 = randint(0, 10)
  value4 = randint(0, 10)
  await asyncio.sleep(0.01)
  kod3 = str(value) + str(value2) + str(value3) + str(value4)
  await asyncio.sleep(0.1)
  language = 'pl'
  tts = gTTS(text=str(value), lang=language, slow=False)
  with open('1kod.mp3', 'wb') as f:
      tts.write_to_fp(f)

  tts1 = gTTS(text=str(value2), lang=language, slow=False)
  with open('2kod.mp3', 'wb') as f:
      tts1.write_to_fp(f)

  tts2 = gTTS(text=str(value3), lang=language, slow=False)
  with open('3kod.mp3', 'wb') as f:
      tts2.write_to_fp(f)

  tts3 = gTTS(text=str(value4), lang=language, slow=False)
  with open('4kod.mp3', 'wb') as f:
      tts3.write_to_fp(f)
  tts4 = gTTS(text=str(member.display_name) + 'Witam serdecznie. W związku z godziną policyjną zostałeś zatrzymany zgodnie z paragrafem 237 regulaminu gejmingowego za nie autoryzowane wejście na kanał. Musisz Wpisać kod w celu weryfikacji. oto i on.', lang=language, slow=False)
  with open('sprawdzam.mp3', 'wb') as f:
      tts4.write_to_fp(f)

  tts5 = gTTS(text=str(member.display_name) + ' Zgadza się. miłego dnia.', lang=language, slow=False)
  with open('wingodzpol.mp3', 'wb') as f:
      tts5.write_to_fp(f)
  tts6 = gTTS(text=str(member.display_name) + ' A teraz proszę podać swoją oryginalną nazwe na diskordzie.', lang=language, slow=False)
  with open('oryginalneimie.mp3', 'wb') as f:
      tts6.write_to_fp(f)
  await asyncio.sleep(0.1)
  currentmembers = channel.members
  quizmembers = channel.members
  await asyncio.sleep(0.1)
  for member2 in channel.members:
      if not member2.display_name == member.display_name:
          if member2 in quizmembers:
              quizmembers.remove(member2)
              print(member2.display_name + " wypierdolono z kolejki")


  await asyncio.sleep(0.1)

  print(kod3)

  print(str(quizmembers))
  await asyncio.sleep(2)
  voice = await channel.connect()
  voice.play(discord.FFmpegPCMAudio( source="policering.mp3"))
  while voice.is_playing():
      await asyncio.sleep(2)
      print('gra przywitanie')
  voice.play(discord.FFmpegPCMAudio( source="sprawdzam.mp3"))
  while voice.is_playing():
      await asyncio.sleep(2)
      print('gra przywitanie')
  print("podaje kod")
  voice.stop()
  voice.play(discord.FFmpegPCMAudio( source="1kod.mp3"))
  await asyncio.sleep(2)
  voice.stop()
  voice.play(discord.FFmpegPCMAudio( source="2kod.mp3"))
  await asyncio.sleep(2)
  voice.stop()
  voice.play(discord.FFmpegPCMAudio( source="3kod.mp3"))
  await asyncio.sleep(2)
  voice.stop()
  voice.play(discord.FFmpegPCMAudio( source="4kod.mp3"))
  await asyncio.sleep(1.5)
  if ktoramuzyka == 1:
      voice.stop()
      await asyncio.sleep(0.1)
      voice.play(discord.FFmpegPCMAudio( source="clock.mp3"))
      print('gram muzyke 1 na wpisywanie kodu!')
  if ktoramuzyka == 2:
      voice.stop()
      await asyncio.sleep(0.1)
      voice.play(discord.FFmpegPCMAudio( source="clock.mp3"))
      print('gram muzyke 2 na wpisywanie kodu!')
  if ktoramuzyka == 3:
      voice.stop()
      await asyncio.sleep(0.1)
      voice.play(discord.FFmpegPCMAudio( source="clock.mp3"))
      print('gram muzyke 3 na wpisywanie kodu!')


  while voice.is_playing():
      await asyncio.sleep(2)
      print('gra quiz')
      if kodpoprawnygodz == 1:
           voice.stop()
           await asyncio.sleep(0.1)
           czywygrana = 1


  if czywygrana is None:
      voice.play(discord.FFmpegPCMAudio( source="shotgun.mp3"))
      czywygrana = None
      sprawdzanie = 0
      nameval = None
      namepoprawny = 0
      kodpoprawnygodz = 0
      hell = discord.utils.find(lambda r: r.name == 'PszczelarzHell', member.guild.roles)
      if not hell in member.roles:
          if member.bot == False:
              await member.add_roles(hell)
              print('dano range')
              print("dano tak tak")
  if czywygrana is not None:
      nameval2 = str(member.name)
      nameval3 = nameval2.lower()
      nameval4 = nameval3.replace(' ', '')
      nameval = nameval4
      print(nameval)
      await asyncio.sleep(2)
      voice.stop()
      voice.play(discord.FFmpegPCMAudio( source="oryginalneimie.mp3"))
      while voice.is_playing():
          await asyncio.sleep(2)
          print('gra quiz')
      if ktoramuzyka == 1:
          voice.play(discord.FFmpegPCMAudio( source="clock.mp3"))
          print('gram muzyke 1 na wpisywanie kodu!')
      if ktoramuzyka == 2:
          voice.play(discord.FFmpegPCMAudio( source="clock.mp3"))
          print('gram muzyke 2 na wpisywanie kodu!')
      if ktoramuzyka == 3:
          voice.play(discord.FFmpegPCMAudio( source="clock.mp3"))
          print('gram muzyke 3 na wpisywanie kodu!')
      while voice.is_playing():
          await asyncio.sleep(2)
          print('gra quiz')
          if namepoprawny == 1:
              voice.stop()
              await asyncio.sleep(0.1)
              voice.play(discord.FFmpegPCMAudio( source="wingodzpol.mp3"))
              czywygrana = 2
              while voice.is_playing():
                  await asyncio.sleep(2)
                  print('gra wygrana')

  if czywygrana == 1:
      voice.play(discord.FFmpegPCMAudio( source="shotgun.mp3"))
      hell = discord.utils.find(lambda r: r.name == 'PszczelarzHell', member.guild.roles)
      czywygrana = None
      sprawdzanie = 0
      nameval = None
      namepoprawny = 0
      kodpoprawnygodz = 0
      if not hell in member.roles:
          if member.bot == False:
              await member.add_roles(hell)
              print('dano range')




  await asyncio.sleep(3)
  for member in channel.members:
      if member in quizmembers:
          quizmembers.remove(member)
          await member.edit(voice_channel= None)
          hell = discord.utils.find(lambda r: r.name == 'PszczelarzHell', member.guild.roles)
          if not hell in member.roles:
              if member.bot == False:
                  await member.add_roles(hell)
                  print('dano range')


  await asyncio.sleep(1)
  czywygrana = None
  sprawdzanie = 0
  nameval = None
  namepoprawny = 0
  kodpoprawnygodz = 0
  await voice.disconnect()
 else:
  if member.id == 264079253757231104 and godzinapol == 1 and sprawdzanie == 0:
        language = 'pl'
        tts = gTTS(text=str(member.display_name) + ' Uszanowanie Prezydencie. Wszystko pod kontrolą.', lang=language, slow=False)
        with open('kierownik.mp3', 'wb') as f:
            tts.write_to_fp(f)
        channel = after.channel
        await asyncio.sleep(2)
        sprawdzanie = 1
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="kierownik.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        await voice.disconnect()
        ktoramuzyka = 0
        sprawdzanie = 0
        czywygrana = None
        sprawdzanie = 0
        nameval = None
        namepoprawny = 0
        kodpoprawnygodz = 0
  if member.id == 212988300137463809 and godzinapol == 1 and sprawdzanie == 0:
         sprawdzanie = 1
         language = 'pl'
         tts = gTTS(text=str(member.display_name) + ' Uszanowanie premierze. Wszystko pod kontrolą.', lang=language, slow=False)
         with open('kierownik.mp3', 'wb') as f:
             tts.write_to_fp(f)
         channel = after.channel
         await asyncio.sleep(2)
         sprawdzanie = 1
         voice = await channel.connect()
         voice.play(discord.FFmpegPCMAudio( source="kierownik.mp3"))
         while voice.is_playing():
             await asyncio.sleep(2)
             print('gra')
         await voice.disconnect()
         ktoramuzyka = 0
         sprawdzanie = 0
         czywygrana = None
         sprawdzanie = 0
         nameval = None
         namepoprawny = 0
         kodpoprawnygodz = 0
  if member.id == 290179026474106881 and godzinapol == 1 and sprawdzanie == 0:
         sprawdzanie = 1
         language = 'pl'
         tts = gTTS(text=str(member.display_name) + ' Uszanowanie dozorco. Wszystko pod kontrolą.', lang=language, slow=False)
         with open('kierownik.mp3', 'wb') as f:
             tts.write_to_fp(f)
         channel = after.channel
         await asyncio.sleep(2)
         sprawdzanie = 1
         voice = await channel.connect()
         voice.play(discord.FFmpegPCMAudio( source="kierownik.mp3"))
         while voice.is_playing():
             await asyncio.sleep(2)
             print('gra')
         await voice.disconnect()
         ktoramuzyka = 0
         sprawdzanie = 0
         czywygrana = None
         sprawdzanie = 0
         nameval = None
         namepoprawny = 0
         kodpoprawnygodz = 0






@client.command()
async def czerepaktheme(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="czerepak.mp3"))
        print('Gram czerep')
        await asyncio.sleep(133)
        await voice.disconnect()
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="czerepak.mp3"))
        print('Gram czerep')
        await asyncio.sleep(133)
        await voice.disconnect()
@client.command()
async def wstawaj(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="wstawaj.mp3"))
        print('Gram wstawaj')
        await asyncio.sleep(38)
        await voice.disconnect()
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="wstawaj.mp3"))
        print('Gram wstawaj')
        await asyncio.sleep(38)
        await voice.disconnect()

@client.command()
async def legia(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="legia.mp3"))
        print('Gram legie')
        await asyncio.sleep(145)
        await voice.disconnect()
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="legia.mp3"))
        print('Gram legie')
        await asyncio.sleep(145)
        await voice.disconnect()

@client.command()
async def jablon(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="jablon.mp3"))
        print('Gram jablona')
        await asyncio.sleep(62)
        await voice.disconnect()
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="jablon.mp3"))
        print('Gram jablona')
        await asyncio.sleep(62)
        await voice.disconnect()

@client.command()
async def pedal(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
        await ctx.message.delete()
        voice.play(discord.FFmpegPCMrAudio( source="pedal.mp3"))
        print('Gram pedal')
        await asyncio.sleep(3)
        await voice.disconnect()
        await ctx.message.delete()
    else:
        voice = await channel.connect()
        await ctx.message.delete()
        voice.play(discord.FFmpegPCMAudio( source="pedal.mp3"))
        print('Gram pedal')
        await asyncio.sleep(3)
        await voice.disconnect()
        await ctx.message.delete()

@client.command()
async def mirmax(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="mirmax.mp3"))
        print('Gram mirmax')
        await asyncio.sleep(5)
        await voice.disconnect()
        print('Wychodze!!!!!')
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="mirmax.mp3"))
        print('Gram mirmax')
        await asyncio.sleep(5)
        await voice.disconnect()
        print('Wychodze!!!!!')





@client.command()
async def mów(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    language = 'pl'
    messagetext = ctx.message.clean_content
    finaltext = messagetext.replace('cody!mów','')
    tts = gTTS(text=finaltext, lang=language, slow=False)
    with open('text.mp3', 'wb') as f:
        tts.write_to_fp(f)

    if voice and voice.is_connected():
        voice.stop()
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="text.mp3"))
        print('Mówie '+ finaltext )
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!!!')

    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="text.mp3"))
        print('Mówie '+ finaltext)
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')








if not os.path.exists('debilewyciszyli.mp3'):
    language = 'pl'
    mytext = 'Trzeba było kurwa nie wyciszać hamie.'
    tts = gTTS(text=mytext, lang=language, slow=False)
    with open('debilewyciszyli.mp3', 'wb') as f:
        tts.write_to_fp(f)

if not os.path.exists('win.mp3'):
    language = 'pl'
    mytext = 'Bardzo dobrze. '
    tts = gTTS(text=mytext, lang=language, slow=False)
    with open('win.mp3', 'wb') as f:
        tts.write_to_fp(f)


if not os.path.exists('wojna1komunikat.mp3'):
    language = 'pl'
    mytext = 'Pamiętajcie że na terytorium obowiązuje cenzura. Prezydent zdecydował by nie wysadzać placówki w związku z paragrafem 2137.'
    tts = gTTS(text=mytext, lang=language, slow=False)
    with open('wojna1komunikat.mp3', 'wb') as f:
        tts.write_to_fp(f)
if not os.path.exists('wysadzamywpizdu.mp3'):
    language = 'pl'
    mytext = 'W ramach bezpieczeństwa aktualne miejsce pobytu zostanie wysadzone.'
    tts = gTTS(text=mytext, lang=language, slow=False)
    with open('wysadzamywpizdu.mp3', 'wb') as f:
        tts.write_to_fp(f)
if not os.path.exists('mynameis.mp3'):
    language = 'pl'
    mytext = 'maj nejm is Pszczelarz bot. bat ewrybady cols mi Pszczelarz'
    tts = gTTS(text=mytext, lang=language, slow=False)
    with open('mynameis.mp3', 'wb') as f:
        tts.write_to_fp(f)
@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def quiz(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    global currentmember
    global kod
    global quizmembers
    global czywygrana
    ktoramuzyka = randint(1, 20)
    value = randint(0, 10)
    value2 = randint(0, 10)
    value3 = randint(0, 10)
    value4 = randint(0, 10)
    await asyncio.sleep(0.01)
    kod = str(value) + str(value2) + str(value3) + str(value4)
    await asyncio.sleep(0.1)
    language = 'pl'
    tts = gTTS(text=str(value), lang=language, slow=False)
    with open('1kod.mp3', 'wb') as f:
        tts.write_to_fp(f)

    tts = gTTS(text=str(value2), lang=language, slow=False)
    with open('2kod.mp3', 'wb') as f:
        tts.write_to_fp(f)

    tts = gTTS(text=str(value3), lang=language, slow=False)
    with open('3kod.mp3', 'wb') as f:
        tts.write_to_fp(f)

    tts = gTTS(text=str(value4), lang=language, slow=False)
    with open('4kod.mp3', 'wb') as f:
        tts.write_to_fp(f)


    await asyncio.sleep(2)
    voice = await channel.connect()
    voice.play(discord.FFmpegPCMAudio( source="quizintro.mp3"))
    print('Uruchomiono quiz!')
    await asyncio.sleep(8)
    voice.stop()
    for member in channel.members:
        if not member.id == 814510016433356834:
            await member.edit(mute=True)
            print('zmutowano go ^')


    currentmembers = channel.members
    quizmembers = channel.members
    await asyncio.sleep(0.1)
    voice.play(discord.FFmpegPCMAudio( source="quiz.mp3"))
    print('przywitanie')


    for member in channel.members:
        if member.bot == True:
            if member in quizmembers:
                quizmembers.remove(member)



    await asyncio.sleep(0.1)
    print(kod)
    await asyncio.sleep(4)
    voice.stop()
    voice.play(discord.FFmpegPCMAudio( source="quizkodto.mp3"))
    await asyncio.sleep(1.8)
    voice.stop()
    voice.play(discord.FFmpegPCMAudio( source="1kod.mp3"))
    await asyncio.sleep(2)
    voice.stop()
    voice.play(discord.FFmpegPCMAudio( source="2kod.mp3"))
    await asyncio.sleep(2)
    voice.stop()
    voice.play(discord.FFmpegPCMAudio( source="3kod.mp3"))
    await asyncio.sleep(2)
    voice.stop()
    voice.play(discord.FFmpegPCMAudio( source="4kod.mp3"))
    await asyncio.sleep(1.5)
    if ktoramuzyka == 1:
        voice.play(discord.FFmpegPCMAudio( source="quizmusic.mp3"))
        print('gram You')
    if ktoramuzyka == 2:
        voice.play(discord.FFmpegPCMAudio( source="quizmusic2.mp3"))
        print('gram Mystery')
    if ktoramuzyka == 3:
        voice.play(discord.FFmpegPCMAudio( source="quizmusic3.mp3"))
        print('gram Nowe spoko jest')
    if ktoramuzyka == 4:
        voice.play(discord.FFmpegPCMAudio( source="quizmusic4.mp3"))
        print('gram Home trap intro')
    if ktoramuzyka == 5:
        voice.play(discord.FFmpegPCMAudio( source="na-wieczor.mp3"))
        print('gram na wieczor')
    if ktoramuzyka == 6:
        voice.play(discord.FFmpegPCMAudio( source="quizmusic5.mp3"))
        print('gram Naughty Boy - La la la ft. Sam Smith')
    if ktoramuzyka == 7:
        voice.play(discord.FFmpegPCMAudio( source="quizmusic6.mp3"))
        print('gram We are alive')
    if ktoramuzyka == 8:
        voice.play(discord.FFmpegPCMAudio( source="chill3.mp3"))
        print('gram chill 3')
    if ktoramuzyka == 9:
        voice.play(discord.FFmpegPCMAudio( source="chill_2-dokurno.mp3"))
        print('gram chill 2 dokurno')
    if ktoramuzyka == 10:
        voice.play(discord.FFmpegPCMAudio( source="xddd.mp3"))
        print('gram xddd')
    if ktoramuzyka == 11:
        voice.play(discord.FFmpegPCMAudio( source="maxchill.mp3"))
        print('gram max chill')
    if ktoramuzyka == 12:
        voice.play(discord.FFmpegPCMAudio( source="najlepszy-projekt-demo1.mp3"))
        print('gram najlepszy projekt demo')
    if ktoramuzyka == 13:
        voice.play(discord.FFmpegPCMAudio( source="Projectdemo.mp3"))
        print('gram Project DEMO')
    if ktoramuzyka == 14:
        voice.play(discord.FFmpegPCMAudio( source="nastrojowe.mp3"))
        print('gram nastrojowe')
    if ktoramuzyka == 15:
        voice.play(discord.FFmpegPCMAudio( source="cosnowego.mp3"))
        print('gram cos nowego')
    if ktoramuzyka == 16:
        voice.play(discord.FFmpegPCMAudio( source="Intoyou.mp3"))
        print('gram Into you ft Ariana Grande')
    if ktoramuzyka == 17:
        voice.play(discord.FFmpegPCMAudio( source="DJJ.mp3"))
        print('gram DJJ')
    if ktoramuzyka == 18:
        voice.play(discord.FFmpegPCMAudio( source="Dziwne.mp3"))
        print('gram Dzwine')
    if ktoramuzyka == 19:
        voice.play(discord.FFmpegPCMAudio( source="Omg.mp3"))
        print('gram OMG')
    if ktoramuzyka == 20:
        voice.play(discord.FFmpegPCMAudio( source="NowyPakietcut.mp3"))
        print('gram nowy pakiet')


    while voice.is_playing():
        await asyncio.sleep(2)
        print('gra quiz')
        if len(quizmembers) == 0:
            voice.stop()
            await asyncio.sleep(0.1)
            voice.play(discord.FFmpegPCMAudio( source="win.mp3"))
            czywygrana = 1
            await asyncio.sleep(1.5)

    if czywygrana is None:
        voice.play(discord.FFmpegPCMAudio( source="debilewyciszyli.mp3"))

    await asyncio.sleep(2)
    for member in channel.members:
            await member.edit(mute=False)
    await asyncio.sleep(2)
    for member in channel.members:
        if member in quizmembers:
            quizmembers.remove(member)
            await member.edit(voice_channel= None)
            hell = discord.utils.find(lambda r: r.name == 'PszczelarzHell', ctx.guild.roles)
            if not hell in member.roles:
                if member.bot == False:
                    await member.add_roles(hell)
                    print('dano range')


    await asyncio.sleep(2)
    czywygrana = None
    await voice.disconnect()


@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def quizobama(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    global currentmember
    global kod
    global quizmembers
    global czywygrana
    ktoramuzyka = 1
    value = randint(1, 10)
    value2 = randint(1, 10)
    value3 = randint(1, 10)
    value4 = randint(1, 10)
    await asyncio.sleep(0.01)
    kod = str(value) + str(value2) + str(value3) + str(value4)
    await asyncio.sleep(0.1)

    await asyncio.sleep(2)
    voice = await channel.connect()
    voice.play(discord.FFmpegPCMAudio( source="obamaintro.mp3"))
    print('Uruchomiono quiz obama!')
    await asyncio.sleep(14)
    voice.stop()
    for member in channel.members:
        if not member.id == 814510016433356834:
            await member.edit(mute=True)
            print('zmutowano go ^')


    currentmembers = channel.members
    quizmembers = channel.members
    await asyncio.sleep(0.1)
    voice.play(discord.FFmpegPCMAudio( source="obamaquizstart.mp3"))
    print('przywitanie')


    for member in channel.members:
        if member.bot == True:
            if member in quizmembers:
                quizmembers.remove(member)



    await asyncio.sleep(0.1)
    print(kod)
    await asyncio.sleep(8)
    voice.stop()
    if value == 1:
        voice.play(discord.FFmpegPCMAudio( source="obama1.mp3"))
        await asyncio.sleep(1.5)
    if value == 2:
        voice.play(discord.FFmpegPCMAudio( source="obama2.mp3"))
        await asyncio.sleep(1.5)
    if value == 3:
        voice.play(discord.FFmpegPCMAudio( source="obama3.mp3"))
        await asyncio.sleep(1.5)
    if value == 4:
        voice.play(discord.FFmpegPCMAudio( source="obama4.mp3"))
        await asyncio.sleep(1.5)
    if value == 5:
        voice.play(discord.FFmpegPCMAudio( source="obama5.mp3"))
        await asyncio.sleep(1.5)
    if value == 6:
        voice.play(discord.FFmpegPCMAudio( source="obama6.mp3"))
        await asyncio.sleep(1.5)
    if value == 7:
        voice.play(discord.FFmpegPCMAudio( source="obama7.mp3"))
        await asyncio.sleep(1.5)
    if value == 8:
        voice.play(discord.FFmpegPCMAudio( source="obama8.mp3"))
        await asyncio.sleep(1.5)
    if value == 9:
        voice.play(discord.FFmpegPCMAudio( source="obama9.mp3"))
        await asyncio.sleep(1.5)
    if value == 10:
        voice.play(discord.FFmpegPCMAudio( source="obama10.mp3"))
        await asyncio.sleep(1.5)

    voice.stop()
    if value2 == 1:
        voice.play(discord.FFmpegPCMAudio( source="obama1.mp3"))
        await asyncio.sleep(1.5)
    if value2 == 2:
        voice.play(discord.FFmpegPCMAudio( source="obama2.mp3"))
        await asyncio.sleep(1.5)
    if value2 == 3:
        voice.play(discord.FFmpegPCMAudio( source="obama3.mp3"))
        await asyncio.sleep(1.5)
    if value2 == 4:
        voice.play(discord.FFmpegPCMAudio( source="obama4.mp3"))
        await asyncio.sleep(1.5)
    if value2 == 5:
        voice.play(discord.FFmpegPCMAudio( source="obama5.mp3"))
        await asyncio.sleep(1.5)
    if value2 == 6:
        voice.play(discord.FFmpegPCMAudio( source="obama6.mp3"))
        await asyncio.sleep(1.5)
    if value2 == 7:
        voice.play(discord.FFmpegPCMAudio( source="obama7.mp3"))
        await asyncio.sleep(1.5)
    if value2 == 8:
        voice.play(discord.FFmpegPCMAudio( source="obama8.mp3"))
        await asyncio.sleep(1.5)
    if value2 == 9:
        voice.play(discord.FFmpegPCMAudio( source="obama9.mp3"))
        await asyncio.sleep(1.5)
    if value2 == 10:
        voice.play(discord.FFmpegPCMAudio( source="obama10.mp3"))
        await asyncio.sleep(1.5)
    voice.stop()
    if value3 == 1:
        voice.play(discord.FFmpegPCMAudio( source="obama1.mp3"))
        await asyncio.sleep(1.5)
    if value3 == 2:
        voice.play(discord.FFmpegPCMAudio( source="obama2.mp3"))
        await asyncio.sleep(1.5)
    if value3 == 3:
        voice.play(discord.FFmpegPCMAudio( source="obama3.mp3"))
        await asyncio.sleep(1.5)
    if value3 == 4:
        voice.play(discord.FFmpegPCMAudio( source="obama4.mp3"))
        await asyncio.sleep(1.5)
    if value3 == 5:
        voice.play(discord.FFmpegPCMAudio( source="obama5.mp3"))
        await asyncio.sleep(1.5)
    if value3 == 6:
        voice.play(discord.FFmpegPCMAudio( source="obama6.mp3"))
        await asyncio.sleep(1.5)
    if value3 == 7:
        voice.play(discord.FFmpegPCMAudio( source="obama7.mp3"))
        await asyncio.sleep(1.5)
    if value3 == 8:
        voice.play(discord.FFmpegPCMAudio( source="obama8.mp3"))
        await asyncio.sleep(1.5)
    if value3 == 9:
        voice.play(discord.FFmpegPCMAudio( source="obama9.mp3"))
        await asyncio.sleep(1.5)
    if value3 == 10:
        voice.play(discord.FFmpegPCMAudio( source="obama10.mp3"))
        await asyncio.sleep(1.5)
    voice.stop()
    if value4 == 1:
        voice.play(discord.FFmpegPCMAudio( source="obama1.mp3"))
        await asyncio.sleep(1.5)
    if value4 == 2:
        voice.play(discord.FFmpegPCMAudio( source="obama2.mp3"))
        await asyncio.sleep(1.5)
    if value4 == 3:
        voice.play(discord.FFmpegPCMAudio( source="obama3.mp3"))
        await asyncio.sleep(1.5)
    if value4 == 4:
        voice.play(discord.FFmpegPCMAudio( source="obama4.mp3"))
        await asyncio.sleep(1.5)
    if value4 == 5:
        voice.play(discord.FFmpegPCMAudio( source="obama5.mp3"))
        await asyncio.sleep(1.5)
    if value4 == 6:
        voice.play(discord.FFmpegPCMAudio( source="obama6.mp3"))
        await asyncio.sleep(1.5)
    if value4 == 7:
        voice.play(discord.FFmpegPCMAudio( source="obama7.mp3"))
        await asyncio.sleep(1.5)
    if value4 == 8:
        voice.play(discord.FFmpegPCMAudio( source="obama8.mp3"))
        await asyncio.sleep(1.5)
    if value4 == 9:
        voice.play(discord.FFmpegPCMAudio( source="obama9.mp3"))
        await asyncio.sleep(1.5)
    if value4 == 10:
        voice.play(discord.FFmpegPCMAudio( source="obama10.mp3"))
        await asyncio.sleep(1.5)
    if ktoramuzyka == 1:
        voice.play(discord.FFmpegPCMAudio( source="obamawpisywanie.mp3"))
        print('gram obama wpisywanie')

    while voice.is_playing():
        await asyncio.sleep(2)
        print('gra quiz')
        if len(quizmembers) == 0:
            voice.stop()
            await asyncio.sleep(0.1)
            voice.play(discord.FFmpegPCMAudio( source="obamawin.mp3"))
            czywygrana = 1
            await asyncio.sleep(2)

    if czywygrana is None:
        voice.play(discord.FFmpegPCMAudio( source="obamafail.mp3"))

    await asyncio.sleep(2)
    for member in channel.members:
            await member.edit(mute=False)
    await asyncio.sleep(2)
    for member in channel.members:
        if member in quizmembers:
            quizmembers.remove(member)
            await member.edit(voice_channel= None)
            hell = discord.utils.find(lambda r: r.name == 'PszczelarzHell', ctx.guild.roles)
            if not hell in member.roles:
                if member.bot == False:
                    await member.add_roles(hell)
                    print('dano range')


    await asyncio.sleep(2)
    czywygrana = None
    await voice.disconnect()





@client.event
async def on_message(message):
    global kod
    global kod2
    global kod3
    global quizmembers
    global randomkick
    global damianvalue
    global creditplusimages
    global czyktoswpisaldamian
    global order66val
    global namepoprawny
    global nameval
    global kodpoprawnygodz
    member = message.author
    messageContent1 = message.content.lower()
    messageContent = messageContent1.replace(' ', '')
    if kod == messageContent:
        print(kod)
        if bool(message.author.guild.get_member(message.author.id)):
            print(message.author.display_name + ' odpowiedział poprawnie')

        if member in quizmembers:
            await message.add_reaction('✅')
            quizmembers.remove(message.author)


    if kod2 == messageContent:
        print(kod2)

        if member in quizmembers:
            await message.add_reaction('✅')
            quizmembers.remove(message.author)


    if kod3 == messageContent:
        if member in quizmembers:
            print(kod3)
            kodpoprawnygodz = 1
            await message.add_reaction('✅')
            if bool(message.author.guild.get_member(message.author.id)):
                print(message.author.display_name + ' odpowiedział poprawnie')



    if damianvalue == messageContent:
        print(damianvalue)
        czyktoswpisaldamian = 1

        if member in quizmembers:
            await message.add_reaction('✅')
            quizmembers.remove(message.author)


    if nameval == messageContent:
        if member in quizmembers:
            namepoprawny = 1
            await message.add_reaction('✅')
            quizmembers.remove(message.author)

    role = discord.utils.get(member.guild.roles, name="wojna")
    if role in member.roles:
        if member.bot == False:
            if not message.content.lower().startswith("cody!"):
                print((member.name)+ ' napisal podczas wojny: ' + (messageContent))
                if "tenor" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "dualipa" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "fortnite" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "syf" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "damian" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "anime" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "jebac" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "jebać" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "debil" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "thanos" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "nuke" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "panda" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "pandy" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "debil" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "seks" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "sex" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "regional" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "" == messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if ":" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if ";" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "http" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                if "darkseid" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "dualipa" in messageContent:
                    await message.delete()
                    print('cenzuruje!')
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                if "blitz" in messageContent:
                    await message.delete()
                    print('cenzuruje!')
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                if ".gif" in messageContent:
                    await message.delete()
                    print('cenzuruje!')
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                if "cdn.discordapp.com" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if ":plantRub:" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if ":degen:" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "pierdol" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "kurw" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if ".png" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if ".jpg" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if ".mp4" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "słab" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "weekend" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "weeknd" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "gówno" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "gowno" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "gufno" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if ":guwno:" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "głupi" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "glupi" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "hamie" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "vidimos" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                if "lgbt" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "pis" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                if "bok" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "toyota" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "nasus" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "spellbook" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "top" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "mid" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "bot" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "las" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "dżungla" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "duahell" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "tft" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "czerep" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "yummi" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "p90" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "offline" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "barka" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "teleturniej" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "dua" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "hamie" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "panie marcinie" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "rythm" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "scp" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "groovy" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "huj" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "Never get high on your own supply" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "harley" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "marvel" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "dc" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "garen" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "smoczasty" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "hubertmoszka" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "jakubtusk" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "wojna" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "gajowik" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "zjeb" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "admin" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "kubado" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "llama" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "protest" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "przywódca" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "veto" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "ichi" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "ras" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "homo" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "fchanez" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "⠛" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "⣶" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "█" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "porn" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "wojn" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "sex" in messageContent:
                    await message.delete()
                    print('cenzuruje!')
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                if "wychodze" in messageContent:
                    await message.delete()
                    print('cenzuruje!')
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                if "leave" in messageContent:
                    await message.delete()
                    print('cenzuruje!')
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                if "serw" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "serv" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "pol" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "dykt" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "precz" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "zbombardowa" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "gta" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "san" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "wygr" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "walk" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "zdelegalizowa" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "cenzu" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "podziemn" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "gej" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "stop" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "liza" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "wsadz" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "cyck" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "cip" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "dup" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "czasty" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "sperm" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "ruch" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "pizd" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "cum" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "kevi" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')
                if "putin" in messageContent:
                    await message.delete()
                    if order66val == 1:
                        var = discord.utils.get(member.guild.roles, name = "PszczelarzHell")
                        await member.add_roles(var)
                    print('cenzuruje!')





    role2 = discord.utils.get(member.guild.roles, name="sus")
    role3 = discord.utils.get(member.guild.roles, name="Muted")
    if role2 in member.roles:
        if member.bot == False:
            if message.attachments or 'https://' in messageContent:
             print('attachment or link found!')
             embed = discord.Embed(title="Stop!", description=str(member.display_name) + ' wysłałeś ostatnio zbyt dużo sus rzeczy byczqu.', colour=discord.Color.red())
             embed.set_thumbnail(url = 'https://www.pngitem.com/pimgs/m/245-2453763_transparent-police-icon-png-police-icon-png-download.png')
             message4 = await message.channel.send(embed=embed)
             await message.delete()
             await member.add_roles(role3)
             print("mute")
             await asyncio.sleep(60)
             await member.remove_roles(role3)
             print("po mute")


    if not role in member.roles or member.id == 264079253757231104:
        await client.process_commands(message)




@quiz.error
async def echo_error(ctx, error):
    member = ctx.message.author
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if isinstance(error, MissingPermissions):
        await ctx.message.delete()
        voice = await channel.connect()
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .Nie masz debilu permisji.', lang=language, slow=False)
        with open('perm.mp3', 'wb') as f:
            tts.write_to_fp(f)
        voice.play(discord.FFmpegPCMAudio( source="perm.mp3"))
        await asyncio.sleep(4)
        await voice.disconnect()
        await ctx.message.delete()


@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def echo(ctx, member: discord.Member):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and not member.id == 814510016433356834 and voice.is_connected():
        await voice.move_to(channel)
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .Aktualnie ma echo. Wyciszam.', lang=language, slow=False)
        with open('echo.mp3', 'wb') as f:
            tts.write_to_fp(f)
        await ctx.message.delete()
        voice.play(discord.FFmpegPCMAudio( source="echo.mp3"))
        await asyncio.sleep(5)
        await member.edit(mute=True)
        await asyncio.sleep(2)
        await voice.disconnect()
    else:
        if not member.id == 814510016433356834:
            voice = await channel.connect()
            language = 'pl'
            tts = gTTS(text=str(member.name) + ' .Aktualnie ma echo. Wyciszam.', lang=language, slow=False)
            with open('echo.mp3', 'wb') as f:
                tts.write_to_fp(f)
            await ctx.message.delete()
            voice.play(discord.FFmpegPCMAudio( source="echo.mp3"))
            await asyncio.sleep(5)
            await member.edit(mute=True)
            await asyncio.sleep(2)
            await voice.disconnect()
        else:
            await ctx.message.delete()
            voice = await channel.connect()
            language = 'pl'
            tts = gTTS(text=str(ctx.message.author.name) + ' .Nie masz debilu permisji!.', lang=language, slow=False)
            with open('perm.mp3', 'wb') as f:
                tts.write_to_fp(f)
            voice.play(discord.FFmpegPCMAudio( source="perm.mp3"))
            await asyncio.sleep(7)
            await voice.disconnect()
            await ctx.message.delete()


@echo.error
async def echo_error(ctx, error):
    member = ctx.message.author
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if isinstance(error, MissingPermissions):
        await ctx.message.delete()
        voice = await channel.connect()
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .Nie masz debilu permisji!.', lang=language, slow=False)
        with open('perm.mp3', 'wb') as f:
            tts.write_to_fp(f)
        voice.play(discord.FFmpegPCMAudio( source="perm.mp3"))
        await asyncio.sleep(4)
        await voice.disconnect()
        await ctx.message.delete()






@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def pierdoli(ctx, member: discord.Member):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and not member.id == 814510016433356834 and voice.is_connected():
        await voice.move_to(channel)
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .Aktualnie pierdoli głupoty. Wyciszam.', lang=language, slow=False)
        with open('pierd.mp3', 'wb') as f:
            tts.write_to_fp(f)
        await ctx.message.delete()
        voice.play(discord.FFmpegPCMAudio( source="pierd.mp3"))
        await asyncio.sleep(5)
        await member.edit(mute=True)
        await asyncio.sleep(2)
        await voice.disconnect()
    else:
        if not member.id == 814510016433356834:
            voice = await channel.connect()
            language = 'pl'
            tts = gTTS(text=str(member.name) + ' .Aktualnie pierdoli głupoty. Wyciszam.', lang=language, slow=False)
            with open('pierd.mp3', 'wb') as f:
                tts.write_to_fp(f)
            await ctx.message.delete()
            voice.play(discord.FFmpegPCMAudio( source="pierd.mp3"))
            await asyncio.sleep(5)
            await member.edit(mute=True)
            await asyncio.sleep(2)
            await voice.disconnect()
        else:
            await ctx.message.delete()
            voice = await channel.connect()
            language = 'pl'
            tts = gTTS(text=str(ctx.message.author.name) + ' .Nie masz debilu permisji!.', lang=language, slow=False)
            with open('perm.mp3', 'wb') as f:
                tts.write_to_fp(f)
            voice.play(discord.FFmpegPCMAudio( source="perm.mp3"))
            await asyncio.sleep(7)
            await voice.disconnect()
            await ctx.message.delete()

@pierdoli.error
async def pierdoli_error(ctx, error):
    member = ctx.message.author
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if isinstance(error, MissingPermissions):
        await ctx.message.delete()
        voice = await channel.connect()
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .Nie masz debilu permisji!.', lang=language, slow=False)
        with open('perm.mp3', 'wb') as f:
            tts.write_to_fp(f)
        voice.play(discord.FFmpegPCMAudio( source="perm.mp3"))
        await asyncio.sleep(7)
        await voice.disconnect()
        await ctx.message.delete()

@client.command()
async def odcisz(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    member = ctx.message.author
    if voice and voice.is_connected():
        await voice.move_to(channel)
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .Chce się odciszyć.', lang=language, slow=False)
        with open('odc.mp3', 'wb') as f:
            tts.write_to_fp(f)
        await ctx.message.delete()
        voice.play(discord.FFmpegPCMAudio( source="odc.mp3"))
        await asyncio.sleep(5)
        await member.edit(mute=False)
        await asyncio.sleep(2)
        await voice.disconnect()
    else:
        voice = await channel.connect()
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .Chce się odciszyć.', lang=language, slow=False)
        with open('odc.mp3', 'wb') as f:
            tts.write_to_fp(f)
        await ctx.message.delete()
        voice.play(discord.FFmpegPCMAudio( source="odc.mp3"))
        await asyncio.sleep(5)
        await member.edit(mute=False)
        await asyncio.sleep(2)
        await voice.disconnect()

@odcisz.error
async def odcisz_error(ctx, error):
    member = ctx.message.author
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if isinstance(error, MissingPermissions):
        await ctx.message.delete()
        voice = await channel.connect()
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .Chcę się odciszyć ale nie może bo nie ma permisji.', lang=language, slow=False)
        with open('perm.mp3', 'wb') as f:
            tts.write_to_fp(f)
        voice.play(discord.FFmpegPCMAudio( source="perm.mp3"))
        await asyncio.sleep(5)
        await voice.disconnect()
        await ctx.message.delete()





@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def unmute(ctx, member: discord.Member):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        await voice.move_to(channel)
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .W ramach łaski administratora zostanie odciszony.', lang=language, slow=False)
        with open('unmute.mp3', 'wb') as f:
            tts.write_to_fp(f)
        await ctx.message.delete()
        voice.play(discord.FFmpegPCMAudio( source="unmute.mp3"))
        await asyncio.sleep(6)
        await member.edit(mute=False)
        await asyncio.sleep(3)
        await voice.disconnect()
    else:
        voice = await channel.connect()
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .W ramach łaski administratora zostanie odciszony.', lang=language, slow=False)
        with open('unmute.mp3', 'wb') as f:
            tts.write_to_fp(f)
        await ctx.message.delete()
        voice.play(discord.FFmpegPCMAudio( source="unmute.mp3"))
        await asyncio.sleep(6)
        await member.edit(mute=False)
        await asyncio.sleep(3)
        await voice.disconnect()


@client.command()
async def wiad(ctx, member: discord.Member):
    channel = member.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    language = 'pl'
    messagetext = ctx.message.clean_content
    final3text = messagetext.replace('cody!wiad','')
    final2text = final3text.replace(member.name,'')
    finaltext4 = final2text.replace('@','')
    finaltext = finaltext4.replace(member.nick,'')
    tts = gTTS(text=finaltext, lang=language, slow=False)
    with open('text2.mp3', 'wb') as f:
        tts.write_to_fp(f)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="text2.mp3"))
        print('Mówie '+ finaltext )
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="text2.mp3"))
        print('Mówie '+ finaltext )
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def wojnap2137(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if ctx.message.author.id == 264079253757231104:
        await ctx.message.add_reaction('✅')
        for member in ctx.message.author.guild.members:
            wojna = discord.utils.find(lambda r: r.name == 'wojna', ctx.message.author.guild.roles)
            if not wojna in member.roles:
                if member.bot == False:
                    await member.add_roles(wojna)
                    print('dano range')
        print('gotowe dawanie rang')
        voice = await channel.connect()
        for member in channel.members:
            if not member.id == 814510016433356834:

                await member.edit(mute=True)
                print('zmutowano go ^')
        print('gotowe mutowanie gram komunikat')
        voice.play(discord.FFmpegPCMAudio( source="wojna.mp3"))
        await asyncio.sleep(46)
        voice.stop()
        print('stopuje komunikat')
        voice.play(discord.FFmpegPCMAudio( source="wojna1komunikat.mp3"))
        embed = discord.Embed(title="A więc Wojna!", description= "Pamiętajcie że na terytorium obowiązuje cenzura.") #,color=Hex code
        await ctx.send(embed=embed)
        await ctx.message.delete()
        await asyncio.sleep(11)
        for member in channel.members:
            print('odmutowuje')
            await member.edit(mute=False)
        print('gotowe odciszanie')
        await asyncio.sleep(2)
        voice.stop()
        await voice.disconnect()
    else:
        print('to nie kubadi')
        language = 'pl'
        await ctx.message.add_reaction('❌')
        voice = await channel.connect()
        tts = gTTS(text=str(ctx.message.author.name) + ' .Nie jesteś prezydentem. Zostajesz poddany egzekucji.', lang=language, slow=False)
        with open('perm.mp3', 'wb') as f:
            tts.write_to_fp(f)
        voice.play(discord.FFmpegPCMAudio( source="perm.mp3"))
        await asyncio.sleep(6)
        await ctx.message.author.edit(voice_channel= None)
        await voice.disconnect()










@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def powojnie(ctx):
    await ctx.message.add_reaction('✅')
    for guild in client.guilds:
        for member in ctx.guild.members:
            wojna = discord.utils.find(lambda r: r.name == 'wojna', ctx.guild.roles)
            if wojna in member.roles:
                await member.remove_roles(wojna)
                print('usuwam range')


    print('gotowe')
    embed = discord.Embed(title="Koniec Wojny!", description="Obostrzenia już nie obowiązują!!!") #,color=Hex code
    await ctx.send(embed=embed)



@powojnie.error
async def powojnie_error(ctx, error):
    member = ctx.message.author
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if isinstance(error, MissingPermissions):
        await ctx.message.add_reaction('❌')
        voice = await channel.connect()
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .Nie jesteś nawet premierem. A więc to zdrada. Zostajesz poddany egzekucji.', lang=language, slow=False)
        with open('perm.mp3', 'wb') as f:
            tts.write_to_fp(f)
        voice.play(discord.FFmpegPCMAudio( source="perm.mp3"))
        await asyncio.sleep(9)
        await member.edit(voice_channel= None)
        await voice.disconnect()




@client.command()
async def lista(ctx):
    await ctx.message.delete()
    for guild in client.guilds:
            for member in ctx.guild.members:
                print(member.name)















@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def quizmiodzix(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    global currentmember
    global kod2
    global quizmembers
    global czywygrana
    global damianvalue
    global czyktoswpisaldamian
    ktoramuzyka = randint(1, 20)
    value = randint(1, 18)
    if value == 1:
        kod2 = "fuzzybrain"
    if value == 2:
        kod2 = "tak"
        damianvalue = "damian"
    if value == 3:
        kod2 = "2018"
    if value == 4:
        kod2 = "skokinarciarskie"
    if value == 5:
        kod2 = "grandchampion"
    if value == 6:
        kod2 = "nuke"
    if value == 7:
        kod2 = "nautilus"
    if value == 8:
        kod2 = "maślankaczekoladowa"
    if value == 9:
        kod2 = "fioletowy"
    if value == 10:
        kod2 = "matrixumo"
    if value == 11:
        kod2 = "xkom"
    if value == 12:
        kod2 = "toyota"
    if value == 13:
        kod2 = "awp"
    if value == 14:
        kod2 = "nie"
        damianvalue = "damian"
    if value == 15:
        kod2 = "może"
    if value == 16:
        kod2 = "mrugacz"
    if value == 17:
        kod2 = "wojownik"
    if value == 18:
        kod2 = "nautilus"
    await asyncio.sleep(2)
    voice = await channel.connect()
    voice.play(discord.FFmpegPCMAudio( source=f"quizintro.mp3"))
    print('Uruchomiono quiz miodzix!')
    await asyncio.sleep(8)
    voice.stop()
    for member in channel.members:
        if not member.id == 814510016433356834:
            await member.edit(mute=True)
            print('zmutowano go ^')


    currentmembers = channel.members
    quizmembers = channel.members
    await asyncio.sleep(0.1)
    voice.play(discord.FFmpegPCMAudio( source="przywitaniequizmiodzix.mp3"))
    for member in channel.members:
        if member.bot == True:
            if member in quizmembers:
                quizmembers.remove(member)


    await asyncio.sleep(0.1)
    print(kod2)
    print(damianvalue)
    print(ktoramuzyka)
    await asyncio.sleep(8.4)
    voice.stop()
    if value == 1:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="ulubionyalbum.mp3"))
        await asyncio.sleep(12)

    if value == 2:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="czydamiantodebil.mp3"))
        await asyncio.sleep(6)

    if value == 3:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="chill2dokurnorok.mp3"))
        ktoramuzyka = 9
        await asyncio.sleep(13)

    if value == 4:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="wjakagregramnalekcjach.mp3"))
        await asyncio.sleep(12)

    if value == 5:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="jakarangarocket.mp3"))
        await asyncio.sleep(12)

    if value == 6:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="mapawcs.mp3"))
        await asyncio.sleep(15)

    if value == 7:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="supportwlolu.mp3"))
        await asyncio.sleep(13)

    if value == 8:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="ulubionynapoj.mp3"))
        await asyncio.sleep(12)

    if value == 9:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="ulubionykolor.mp3"))
        await asyncio.sleep(11)


    if value == 10:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="starynick.mp3"))
        await asyncio.sleep(14)

    if value == 11:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="sklepkomp.mp3"))
        await asyncio.sleep(10)

    if value == 12:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="toyotaquiz.mp3"))
        await asyncio.sleep(11)

    if value == 13:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="broncs.mp3"))
        await asyncio.sleep(12)

    if value == 14:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="hiszp.mp3"))
        await asyncio.sleep(9)

    if value == 15:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="albumlipy.mp3"))
        await asyncio.sleep(10)

    if value == 16:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="ktoryscp.mp3"))
        await asyncio.sleep(11)

    if value == 17:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="profesjamiodka.mp3"))
        await asyncio.sleep(11)
    if value == 18:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="miodekearrape.mp3"))
        await asyncio.sleep(1.4)


    voice.stop()
    if ktoramuzyka == 1:
        voice.play(discord.FFmpegPCMAudio( source="quizmusic.mp3"))
        print('gram You')
    if ktoramuzyka == 2:
        voice.play(discord.FFmpegPCMAudio( source="quizmusic2.mp3"))
        print('gram Mystery')
    if ktoramuzyka == 3:
        voice.play(discord.FFmpegPCMAudio( source="quizmusic3.mp3"))
        print('gram Nowe spoko jest')
    if ktoramuzyka == 4:
        voice.play(discord.FFmpegPCMAudio( source="quizmusic4.mp3"))
        print('gram Home trap intro')
    if ktoramuzyka == 5:
        voice.play(discord.FFmpegPCMAudio( source="na-wieczor.mp3"))
        print('gram na wieczor')
    if ktoramuzyka == 6:
        voice.play(discord.FFmpegPCMAudio( source="quizmusic5.mp3"))
        print('gram Naughty Boy - La la la ft. Sam Smith')
    if ktoramuzyka == 7:
        voice.play(discord.FFmpegPCMAudio( source="quizmusic6.mp3"))
        print('gram We are alive')
    if ktoramuzyka == 8:
        voice.play(discord.FFmpegPCMAudio( source="chill3.mp3"))
        print('gram chill 3')
    if ktoramuzyka == 9:
        voice.play(discord.FFmpegPCMAudio( source="chill_2-dokurno.mp3"))
        print('gram chill 2 dokurno')
    if ktoramuzyka == 10:
        voice.play(discord.FFmpegPCMAudio( source="xddd.mp3"))
        print('gram xddd')
    if ktoramuzyka == 11:
        voice.play(discord.FFmpegPCMAudio( source="maxchill.mp3"))
        print('gram max chill')
    if ktoramuzyka == 12:
        voice.play(discord.FFmpegPCMAudio( source="najlepszy-projekt-demo1.mp3"))
        print('gram najlepszy projekt demo')
    if ktoramuzyka == 13:
        voice.play(discord.FFmpegPCMAudio( source="Projectdemo.mp3"))
        print('gram Project DEMO')
    if ktoramuzyka == 14:
        voice.play(discord.FFmpegPCMAudio( source="nastrojowe.mp3"))
        print('gram nastrojowe')
    if ktoramuzyka == 15:
        voice.play(discord.FFmpegPCMAudio( source="cosnowego.mp3"))
        print('gram cos nowego')
    if ktoramuzyka == 16:
        voice.play(discord.FFmpegPCMAudio( source="Intoyou.mp3"))
        print('gram Into you ft Ariana Grande')
    if ktoramuzyka == 17:
        voice.play(discord.FFmpegPCMAudio( source="DJJ.mp3"))
        print('gram DJJ')
    if ktoramuzyka == 18:
        voice.play(discord.FFmpegPCMAudio( source="Dziwne.mp3"))
        print('gram Dzwine')
    if ktoramuzyka == 19:
        voice.play(discord.FFmpegPCMAudio( source="Omg.mp3"))
        print('gram OMG')
    if ktoramuzyka == 20:
        voice.play(discord.FFmpegPCMAudio( source="NowyPakietcut.mp3"))
        print('gram nowy pakiet')

    while voice.is_playing():
        await asyncio.sleep(2)
        print('gra quiz')
        if len(quizmembers) == 0:
            voice.stop()
            await asyncio.sleep(0.1)
            if czyktoswpisaldamian == 1:
                voice.play(discord.FFmpegPCMAudio( source="pedal.mp3"))
                czywygrana = 1
                await asyncio.sleep(3)
            else:
                voice.play(discord.FFmpegPCMAudio( source="brawoquiz.mp3"))
                czywygrana = 1
                await asyncio.sleep(4)


    if czywygrana is None:
        voice.play(discord.FFmpegPCMAudio( source="przegranaquizmiodzix.mp3"))

    await asyncio.sleep(2)
    for member in channel.members:
            await member.edit(mute=False)
    await asyncio.sleep(2)
    for member in channel.members:
        if member in quizmembers:
            quizmembers.remove(member)
            await member.edit(voice_channel= None)
            hell = discord.utils.find(lambda r: r.name == 'PszczelarzHell', ctx.guild.roles)
            if not hell in member.roles:
                if member.bot == False:
                    await member.add_roles(hell)
                    print('dano range')


    await asyncio.sleep(2)
    czywygrana = None
    damianvalue = None
    czyktoswpisaldamian = None
    await voice.disconnect()








@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def spojler(ctx, member: discord.Member):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        await voice.move_to(channel)
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .Aktualnie spojleruje film. Wyciszam!!!!', lang=language, slow=False)
        with open('pierd.mp3', 'wb') as f:
            tts.write_to_fp(f)
        await ctx.message.delete()
        voice.play(discord.FFmpegPCMAudio( source="pierd.mp3"))
        await asyncio.sleep(5)
        await member.edit(mute=True)
        await asyncio.sleep(2)
        await voice.disconnect()
    else:
        voice = await channel.connect()
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .Aktualnie spojleruje film. Wyciszam.', lang=language, slow=False)
        with open('pierd.mp3', 'wb') as f:
            tts.write_to_fp(f)
        await ctx.message.delete()
        voice.play(discord.FFmpegPCMAudio( source="pierd.mp3"))
        await asyncio.sleep(5)
        await member.edit(mute=True)
        await asyncio.sleep(2)
        await voice.disconnect()
@pierdoli.error
async def spojler_error(ctx, error):
    member = ctx.message.author
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if isinstance(error, MissingPermissions):
        await ctx.message.delete()
        voice = await channel.connect()
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .Nie masz debilu permisji.', lang=language, slow=False)
        with open('perm.mp3', 'wb') as f:
            tts.write_to_fp(f)
        voice.play(discord.FFmpegPCMAudio( source="perm.mp3"))
        await asyncio.sleep(7)
        await voice.disconnect()
        await ctx.message.delete()

@client.command()
async def miodekpojebie(ctx, member: discord.Member):
    channel = member.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="pojebane.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="pojebane.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def toyota2(ctx, member: discord.Member):
    channel = member.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="toyota.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="toyota.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')


@client.command()
async def toyota(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="toyota.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="toyota.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')


@client.command()
async def dom2(ctx, member: discord.Member):
    channel = member.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    global randomkick
    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="dom.mp3"))
        randomkick = channel.members
        language = 'pl'
        for member in channel.members:
            if member.bot == True:
                if member in randomkick:
                    randomkick.remove(member)
        kickuje = random.choice(randomkick)
        print(kickuje)
        tts = gTTS(text=str(kickuje.name) + 'Aktualnie idzie do domu. Wywalam', lang=language, slow=False)
        with open('domwywalam.mp3', 'wb') as f:
            tts.write_to_fp(f)
        await ctx.message.delete()
        await asyncio.sleep(11)
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="domwywalam.mp3"))
        await asyncio.sleep(6)
        await kickuje.edit(voice_channel= None)
        await voice.disconnect()
        randomkick = None

    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="dom.mp3"))
        randomkick = channel.members
        language = 'pl'
        for member in channel.members:
            if member.bot == True:
                if member in randomkick:
                    randomkick.remove(member)
        kickuje = random.choice(randomkick)
        print(kickuje)
        tts = gTTS(text=str(kickuje.name) + 'Aktualnie idzie do domu. Wywalam', lang=language, slow=False)
        with open('domwywalam.mp3', 'wb') as f:
            tts.write_to_fp(f)
        await ctx.message.delete()
        await asyncio.sleep(11)
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="domwywalam.mp3"))
        await asyncio.sleep(6)
        await kickuje.edit(voice_channel= None)
        await voice.disconnect()
        randomkick = None

@client.command()
async def dom(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    global randomkick
    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="dom.mp3"))
        randomkick = channel.members
        language = 'pl'
        for member in channel.members:
            if member.bot == True:
                if member in randomkick:
                    randomkick.remove(member)
        kickuje = random.choice(randomkick)
        print(kickuje)
        tts = gTTS(text=str(kickuje.name) + 'Aktualnie idzie do domu. Wywalam', lang=language, slow=False)
        with open('domwywalam.mp3', 'wb') as f:
            tts.write_to_fp(f)
        await ctx.message.delete()
        await asyncio.sleep(11)
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="domwywalam.mp3"))
        await asyncio.sleep(6)
        await kickuje.edit(voice_channel= None)
        await voice.disconnect()
        randomkick = None

    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="dom.mp3"))
        randomkick = channel.members
        language = 'pl'
        for member in channel.members:
            if member.bot == True:
                if member in randomkick:
                    randomkick.remove(member)
        await asyncio.sleep(2)
        kickuje = random.choice(randomkick)
        print(kickuje)
        tts = gTTS(text=str(kickuje.name) + 'Aktualnie idzie do domu. Wywalam', lang=language, slow=False)
        with open('domwywalam.mp3', 'wb') as f:
            tts.write_to_fp(f)
        await ctx.message.delete()
        await asyncio.sleep(11)
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="domwywalam.mp3"))
        await asyncio.sleep(6)
        await kickuje.edit(voice_channel= None)
        await voice.disconnect()
        randomkick = None


@client.command()
async def cyberpunk(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="michal.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="michal.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')



@client.command()
async def cyberpunk2(ctx, member: discord.Member):
    channel = member.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="michal.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="michal.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def egzekucja(ctx, member: discord.Member):
    channel = member.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    language = 'pl'
    tts = gTTS(text=str('Witamy w publicznej egzekucji.'+ (member.name)+ 'za złamanie zasad zostanie rozstrzelany'), lang=language, slow=False)
    with open('egzekucja.mp3', 'wb') as f:
        tts.write_to_fp(f)
    await asyncio.sleep(2)
    obywatel = member
    if not obywatel.id == 264079253757231104:
        voice = await channel.connect()
        print(obywatel)
        for member in channel.members:
            if not member.id == 814510016433356834:
                await member.edit(mute=True)
                print('zmutowano go ^')
        await asyncio.sleep(0.5)
        print(obywatel)
        voice.play(discord.FFmpegPCMAudio( source="egzekucja.mp3"))
        await asyncio.sleep(8)
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="shotgun.mp3"))
        await asyncio.sleep(5)
        await obywatel.edit(voice_channel= None)
        print('wywalono ' + (obywatel.name))
        await ctx.message.delete()
        for member in channel.members:
            await member.edit(mute=False)
            print('odmutowano go ^')
        role = discord.utils.get(member.guild.roles, id = 789210196840939601)
        await voice.disconnect()
        await obywatel.add_roles(role)
    else:
        print('On chce zajebac prezydenta!')
        language = 'pl'
        await ctx.message.add_reaction('❌')
        voice = await channel.connect()
        tts = gTTS(text=str(ctx.message.author.name) + ' Dopuścił się zdrady stanu. Zostajesz wtrącony do gułagu.', lang=language, slow=False)
        with open('perm.mp3', 'wb') as f:
            tts.write_to_fp(f)
        voice.play(discord.FFmpegPCMAudio( source="perm.mp3"))
        await asyncio.sleep(6)
        await ctx.message.author.edit(voice_channel= None)
        await voice.disconnect()
        await ctx.message.delete()

@client.command()
async def wojna(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if ctx.message.author.id == 264079253757231104:
        await ctx.message.add_reaction('✅')
        for member in ctx.message.author.guild.members:
            wojna = discord.utils.find(lambda r: r.name == 'wojna', ctx.message.author.guild.roles)
            if not wojna in member.roles:
                if member.bot == False:
                    await member.add_roles(wojna)
                    print('dano range')

        print('gotowe dawanie rang')
        voice = await channel.connect()
        for member in channel.members:
            if not member.id == 814510016433356834:

                await member.edit(mute=True)
                print('zmutowano go ^')
        print('gotowe mutowanie gram komunikat')
        voice.play(discord.FFmpegPCMAudio( source="wojna.mp3"))
        await asyncio.sleep(46)
        voice.stop()
        print('stopuje komunikat')
        for member in channel.members:
            print('odmutowuje')
            await member.edit(mute=False)
        print('gotowe odciszanie')
        await asyncio.sleep(2)
        print('info o wysadzeniu')
        voice.play(discord.FFmpegPCMAudio( source="wysadzamywpizdu.mp3"))
        await asyncio.sleep(5)
        voice.stop()
        await asyncio.sleep(2)
        print('glowica')
        voice.play(discord.FFmpegPCMAudio( source="glowica.mp3"))
        embed = discord.Embed(title="A więc Wojna!", description= "Pamiętajcie że na terytorium obowiązuje cenzura.") #,color=Hex code
        await ctx.send(embed=embed)
        await ctx.message.delete()
        await asyncio.sleep(104)
        await channel.delete()

        print('wysadzono!')
        await voice.disconnect()

    else:
        print('to nie kubadi')
        language = 'pl'
        await ctx.message.add_reaction('❌')
        voice = await channel.connect()
        tts = gTTS(text=str(ctx.message.author.name) + ' .Nie jesteś prezydentem. Zostajesz poddany egzekucji.', lang=language, slow=False)
        with open('perm.mp3', 'wb') as f:
            tts.write_to_fp(f)
        voice.play(discord.FFmpegPCMAudio( source="perm.mp3"))
        await asyncio.sleep(6)
        await ctx.message.author.edit(voice_channel= None)
        await voice.disconnect()

@client.command()
async def wojnap76(ctx):
    if ctx.message.author.id == 264079253757231104:
        await ctx.message.add_reaction('✅')
        for member in ctx.message.author.guild.members:
            wojna = discord.utils.find(lambda r: r.name == 'wojna', ctx.message.author.guild.roles)
            if not wojna in member.roles:
                if member.bot == False:
                    await member.add_roles(wojna)
                    print('dano range')

        print('gotowe dawanie rang')
        embed = discord.Embed(title="A więc Wojna!", description= "Pamiętajcie że na terytorium obowiązuje cenzura.") #,color=Hex code
        await ctx.send(embed=embed)
        await ctx.message.delete()

    else:
        print('to nie kubadi')
        language = 'pl'
        await ctx.message.add_reaction('❌')
        channel = ctx.message.author.voice.channel
        voice = await channel.connect()
        tts = gTTS(text=str(ctx.message.author.name) + ' .Nie jesteś prezydentem. Zostajesz poddany egzekucji.', lang=language, slow=False)
        with open('perm.mp3', 'wb') as f:
            tts.write_to_fp(f)
        voice.play(discord.FFmpegPCMAudio( source="perm.mp3"))
        await asyncio.sleep(6)
        await ctx.message.author.edit(voice_channel= None)
        await voice.disconnect()


@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def las(ctx, member: discord.Member):
    channel = member.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    language = 'pl'
    tts = gTTS(text=str((member.display_name)+ 'do lasu'+(member.display_name)+ 'do lasu'+(member.display_name)+ 'do lasu'+(member.display_name)+ 'do lasu'+(member.display_name)+ 'do lasu'+(member.display_name)+ 'do lasu'+(member.display_name)+ 'do lasu'+(member.display_name)+ 'do lasu'+(member.display_name)+ 'do lasu'+(member.display_name)+ 'do lasu'+(member.display_name)+ 'do lasu'+(member.display_name)+ 'do lasu'+(member.display_name)+ 'do lasu'+(member.display_name)+ 'do lasu'), lang=language, slow=False)
    with open('las.mp3', 'wb') as f:
        tts.write_to_fp(f)
    await asyncio.sleep(2)
    obywatel = member
    await asyncio.sleep(2)
    voice = await channel.connect()
    await ctx.message.delete()
    voice.play(discord.FFmpegPCMAudio( source="las.mp3"))
    while voice.is_playing():
        print('gra')
        await asyncio.sleep(2)
    await voice.disconnect()
    print('wychodze!!!')

@client.command()
async def nautilus(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="lalali.mp3"))
        await ctx.message.delete()
        await asyncio.sleep(6)
        voice.play(discord.FFmpegPCMAudio( source="miodekearrape.mp3"))
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="lalali.mp3"))
        await ctx.message.delete()
        await asyncio.sleep(6)
        voice.play(discord.FFmpegPCMAudio( source="miodekearrape.mp3"))
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def legia2(ctx, member: discord.Member):
    channel = member.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="legia.mp3"))
        print('Gram legie')
        await asyncio.sleep(145)
        await voice.disconnect()
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="legia.mp3"))
        print('Gram legie')
        await asyncio.sleep(145)
        await voice.disconnect()

@client.command()
async def name(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="mynameispszczelarz.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="mynameispszczelarz.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def amogus(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="amogus.mp3", **FFMPEG_OPTIONS2))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="amogus.mp3", **FFMPEG_OPTIONS2))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def dobryjezu(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="dobryjezu.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="dobryjezu.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def sprawdz(ctx, gosciu: discord.Member):
    channel = gosciu.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    global currentmember
    global kod
    global quizmembers
    global czywygrana
    ktoramuzyka = 1
    value = randint(0, 10)
    value2 = randint(0, 10)
    value3 = randint(0, 10)
    value4 = randint(0, 10)
    await asyncio.sleep(0.01)
    kod = str(value) + str(value2) + str(value3) + str(value4)
    await asyncio.sleep(0.1)
    language = 'pl'
    tts = gTTS(text=str(value), lang=language, slow=False)
    with open('1kod.mp3', 'wb') as f:
        tts.write_to_fp(f)

    tts = gTTS(text=str(value2), lang=language, slow=False)
    with open('2kod.mp3', 'wb') as f:
        tts.write_to_fp(f)

    tts = gTTS(text=str(value3), lang=language, slow=False)
    with open('3kod.mp3', 'wb') as f:
        tts.write_to_fp(f)

    tts = gTTS(text=str(value4), lang=language, slow=False)
    with open('4kod.mp3', 'wb') as f:
        tts.write_to_fp(f)
    tts = gTTS(text=str(gosciu.display_name) + 'Siemano. Sprawdzam czy masz mnie wyciszonego. Musisz Wpisać kod w celu weryfikacji. oto i on.', lang=language, slow=False)
    with open('sprawdzam.mp3', 'wb') as f:
        tts.write_to_fp(f)

    currentmembers = channel.members
    quizmembers = channel.members
    await asyncio.sleep(0.1)
    for member in channel.members:
        if not member.display_name == gosciu.display_name:
            if member in quizmembers:
                quizmembers.remove(member)


    await asyncio.sleep(0.1)

    print(kod)


    await asyncio.sleep(4)
    voice = await channel.connect()
    voice.play(discord.FFmpegPCMAudio( source="sprawdzam.mp3"))
    while voice.is_playing():
        await asyncio.sleep(2)
        print('gra przywitanie')
    print("podaje kod")
    voice.stop()
    voice.play(discord.FFmpegPCMAudio( source="1kod.mp3"))
    await asyncio.sleep(2)
    voice.stop()
    voice.play(discord.FFmpegPCMAudio( source="2kod.mp3"))
    await asyncio.sleep(2)
    voice.stop()
    voice.play(discord.FFmpegPCMAudio( source="3kod.mp3"))
    await asyncio.sleep(2)
    voice.stop()
    voice.play(discord.FFmpegPCMAudio( source="4kod.mp3"))
    await asyncio.sleep(1.5)
    if ktoramuzyka == 1:
        voice.play(discord.FFmpegPCMAudio( source="jp2disco.mp3"))
        print('gram muzyke 1 na wpisywanie kodu!')
    if ktoramuzyka == 2:
        voice.play(discord.FFmpegPCMAudio( source="quizmusic2.mp3"))
        print('gram muzyke 2 na wpisywanie kodu!')
    if ktoramuzyka == 3:
        voice.play(discord.FFmpegPCMAudio( source="quizmusic3.mp3"))
        print('gram muzyke 3 na wpisywanie kodu!')


    while voice.is_playing():
        await asyncio.sleep(2)
        print('gra quiz')
        if len(quizmembers) == 0:
            voice.stop()
            await asyncio.sleep(0.1)
            voice.play(discord.FFmpegPCMAudio( source="win.mp3"))
            czywygrana = 1
            await asyncio.sleep(1.5)

    if czywygrana is None:
        voice.play(discord.FFmpegPCMAudio( source="debilewyciszyli.mp3"))

    await asyncio.sleep(4)
    for member in channel.members:
        if member in quizmembers:
            quizmembers.remove(member)
            await member.edit(voice_channel= None)
            hell = discord.utils.find(lambda r: r.name == 'PszczelarzHell', ctx.guild.roles)
            if not hell in member.roles:
                if member.bot == False:
                    await member.add_roles(hell)
                    print('dano range')


    await asyncio.sleep(2)
    czywygrana = None
    await ctx.message.delete()
    await voice.disconnect()

@client.command()
async def h(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="hnieme.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="hnieme.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def bass(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="ineedbass.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="ineedbass.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def wieczor(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="wieczor.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="wieczor.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')


@client.command()
async def chinczykgaming(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="chinczyk.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="chinczyk.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def chingchenghanji(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="ching.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="ching.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def chinczykgaming2(ctx, member: discord.Member):
    channel = member.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="chinczyk.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="chinczyk.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def gumisie(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="gumisie.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="gumisie.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def zadzwon(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    valuektodobiera = randint(1, 2)
    if voice and voice.is_connected():
        await voice.move_to(channel)
        valuektodobiera = randint(1, 2)
        voice.play(discord.FFmpegPCMAudio( source="call.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        if valuektodobiera == 1:
            voice.play(discord.FFmpegPCMAudio( source="ropa.mp3"))
            print('gram rope')
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        if valuektodobiera == 2:
            voice.play(discord.FFmpegPCMAudio( source="ropa.mp3"))
            print('gram rope 2')
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:
        voice = await channel.connect()
        valuektodobiera = randint(1, 2)
        voice.play(discord.FFmpegPCMAudio( source="call.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        if valuektodobiera == 1:
            voice.play(discord.FFmpegPCMAudio( source="ropa.mp3"))
            print('gram rope')
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        if valuektodobiera == 2:
            voice.play(discord.FFmpegPCMAudio( source="ropa.mp3"))
            print('gram rope 2')
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def stopamongus(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="among.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="among.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def hujciwdupe(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="hujci.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="hujci.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')


@client.command()
async def hujciwdupe2(ctx, member: discord.Member):
    channel = member.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="hujci.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="hujci.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def miodzixalbum(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="quizmusic.mp3"))
        print('gram You')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="quizmusic2.mp3"))
        print('gram Mystery')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="quizmusic3.mp3"))
        print('gram Nowe spoko jest')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="quizmusic4.mp3"))
        print('gram Home trap intro')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="na-wieczor.mp3"))
        print('gram na wieczor')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="quizmusic5.mp3"))
        print('gram Naughty Boy - La la la ft. Sam Smith')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="quizmusic6.mp3"))
        print('gram We are alive')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="chill3.mp3"))
        print('gram chill 3')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="chill_2-dokurno.mp3"))
        print('gram chill 2 dokurno')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="xddd.mp3"))
        print('gram xddd')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="maxchill.mp3"))
        print('gram max chill')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="najlepszy-projekt-demo1.mp3"))
        print('gram najlepszy projekt demo')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="Projectdemo.mp3"))
        print('gram Project DEMO')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="nastrojowe.mp3"))
        print('gram nastrojowe')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="cosnowego.mp3"))
        print('gram cos nowego')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="DJJ.mp3"))
        print('gram Djj')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="Dziwne.mp3"))
        print('gram Dziwne')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="Omg.mp3"))
        print('gram OMG')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="NowyPakietcut.mp3"))
        print('gram nowypakiet')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        await voice.disconnect()
        print('wychodze')
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="quizmusic.mp3"))
        print('gram You')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="quizmusic2.mp3"))
        print('gram Mystery')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="quizmusic3.mp3"))
        print('gram Nowe spoko jest')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="quizmusic4.mp3"))
        print('gram Home trap intro')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="na-wieczor.mp3"))
        print('gram na wieczor')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="quizmusic5.mp3"))
        print('gram Naughty Boy - La la la ft. Sam Smith')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="quizmusic6.mp3"))
        print('gram We are alive')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="chill3.mp3"))
        print('gram chill 3')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="chill_2-dokurno.mp3"))
        print('gram chill 2 dokurno')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="xddd.mp3"))
        print('gram xddd')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="maxchill.mp3"))
        print('gram max chill')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="najlepszy-projekt-demo1.mp3"))
        print('gram najlepszy projekt demo')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="Projectdemo.mp3"))
        print('gram Project DEMO')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="nastrojowe.mp3"))
        print('gram nastrojowe')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="cosnowego.mp3"))
        print('gram cos nowego')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="MIODZIX_PROJECT.mp3"))
        print('gram MIODZIX_PROJECT')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="Intoyou.mp3"))
        print('gram Into you ft Ariana Grande')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="DJJ.mp3"))
        print('gram Djj')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="Dziwne.mp3"))
        print('gram Dziwne')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="Omg.mp3"))
        print('gram OMG')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="NowyPakietcut.mp3"))
        print('gram nowypakiet')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        await voice.disconnect()
        print('wychodze')

@client.command()
async def miodzixalbumfull(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegOpusAudio( source="chill3full.mp3"))
        print('gram chill 3')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="Youfull.mp3"))
        print('gram You')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="mysteryfull.mp3"))
        print('gram Mystery')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="spokojestfull.mp3"))
        print('gram Nowe spoko jest')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="homefull.mp3"))
        print('gram Home trap intro')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="nawieczorfull.mp3"))
        print('gram na wieczor')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="lalalafull.mp3"))
        print('gram Naughty Boy - La la la ft. Sam Smith')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="wearealivefull.mp3"))
        print('gram We are alive')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="chill2dokfull.mp3"))
        print('gram chill 2 dokurno')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="projectdemo2full.mp3"))
        print('gram projectdemo2full')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="maxchillfull.mp3"))
        print('gram max chill')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="najlepszyprojektfull.mp3"))
        print('gram najlepszy projekt demo')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="projectdemofull.mp3"))
        print('gram Project DEMO')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="nastrojowefull.mp3"))
        print('gram nastrojowe')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="cosnowegofull.mp3"))
        print('gram cos nowego')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="djjfull.mp3"))
        print('gram Djj')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="dziwnefull.mp3"))
        print('gram Dziwne')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="omgfull.mp3"))
        print('gram OMG')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="MIODZIX_PROJECT.mp3"))
        print('gram MIODZIX_PROJECT')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="Intoyoufull.mp3"))
        print('gram Into you ft Ariana Grande')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="indierockfull.mp3"))
        print('gram INDIE ROCK')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="NowyPakiet.mp3"))
        print('gram Nowy pakiet')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="xylofull.mp3"))
        print('gram XYLO')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="game3full.mp3"))
        print('gram game 3')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="historiafull.mp3"))
        print('gram robilem to cos gdy mialem sie do historii uczyc')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="onlypianofull.mp3"))
        print('gram onlypiano ')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        await voice.disconnect()
        print('wychodze')
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="chill3full.mp3"))
        print('gram chill 3')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="Youfull.mp3"))
        print('gram You')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="mysteryfull.mp3"))
        print('gram Mystery')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="spokojestfull.mp3"))
        print('gram Nowe spoko jest')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="homefull.mp3"))
        print('gram Home trap intro')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="nawieczorfull.mp3"))
        print('gram na wieczor')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="lalalafull.mp3"))
        print('gram Naughty Boy - La la la ft. Sam Smith')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="wearealivefull.mp3"))
        print('gram We are alive')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="chill3full.mp3"))
        print('gram chill 3')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="chill2dokfull.mp3"))
        print('gram chill 2 dokurno')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="projectdemo2full.mp3"))
        print('gram projectdemo2full')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="maxchillfull.mp3"))
        print('gram max chill')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="najlepszyprojektfull.mp3"))
        print('gram najlepszy projekt demo')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="projectdemofull.mp3"))
        print('gram Project DEMO')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="nastrojowefull.mp3"))
        print('gram nastrojowe')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="cosnowegofull.mp3"))
        print('gram cos nowego')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="djjfull.mp3"))
        print('gram Djj')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="dziwnefull.mp3"))
        print('gram Dziwne')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="omgfull.mp3"))
        print('gram OMG')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="MIODZIX_PROJECT.mp3"))
        print('gram MIODZIX_PROJECT')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="Intoyoufull.mp3"))
        print('gram Into you ft Ariana Grande')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="indierockfull.mp3"))
        print('gram INDIE ROCK')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="NowyPakiet.mp3"))
        print('gram Nowy pakiet')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="xylofull.mp3"))
        print('gram XYLO')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="game3full.mp3"))
        print('gram game 3')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="historiafull.mp3"))
        print('gram robilem to cos gdy mialem sie do historii uczyc')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        voice.play(discord.FFmpegPCMAudio( source="onlypianofull.mp3"))
        print('gram onlypiano ')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        await voice.disconnect()
        print('wychodze')


@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def pierdolif(ctx, member: discord.Member):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and not member.id == 814510016433356834 and voice.is_connected():
        await voice.move_to(channel)
        language = 'pl'
        tts = gTTS(text=str(member.name) + ' .Aktualnie pierdoli głupoty. Wyciszam. ', lang=language, slow=False)
        with open('pierd.mp3', 'wb') as f:
            tts.write_to_fp(f)
        tts2 = gTTS(text=' HA HA HA PRANK. debilu. ', lang=language, slow=False)
        with open('prankpierd.mp3', 'wb') as f:
            tts2.write_to_fp(f)
        await ctx.message.delete()
        voice.play(discord.FFmpegPCMAudio( source="pierd.mp3"))
        await asyncio.sleep(5)
        await member.edit(mute=True)
        await asyncio.sleep(2)
        voice.play(discord.FFmpegPCMAudio( source="prankpierd.mp3"))
        await member.edit(mute=False)
        await asyncio.sleep(5)
        await voice.disconnect()
    else:
        if not member.id == 814510016433356834:
            voice = await channel.connect()
            language = 'pl'
            tts = gTTS(text=str(member.name) + ' .Aktualnie pierdoli głupoty. Wyciszam. ', lang=language, slow=False)
            with open('pierd.mp3', 'wb') as f:
                tts.write_to_fp(f)
            tts2 = gTTS(text=' HA HA HA PRANK. debilu. ', lang=language, slow=False)
            with open('prankpierd.mp3', 'wb') as f:
                tts2.write_to_fp(f)
            await ctx.message.delete()
            voice.play(discord.FFmpegPCMAudio( source="pierd.mp3"))
            await asyncio.sleep(5)
            await member.edit(mute=True)
            await asyncio.sleep(2)
            voice.play(discord.FFmpegPCMAudio( source="prankpierd.mp3"))
            await member.edit(mute=False)
            await asyncio.sleep(5)
            await voice.disconnect()
        else:
            await ctx.message.delete()
            voice = await channel.connect()
            language = 'pl'
            tts = gTTS(text=str(ctx.message.author.name) + ' .Nie masz debilu permisji!.', lang=language, slow=False)
            with open('perm.mp3', 'wb') as f:
                tts.write_to_fp(f)
            voice.play(discord.FFmpegPCMAudio( source="perm.mp3"))
            await asyncio.sleep(7)
            await voice.disconnect()
            await ctx.message.delete()

@client.command()
async def mundo(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="mundo.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="mundo.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def fraszka(ctx):
    language = 'pl'
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    ktoramuzyka = randint(1, 8)
    tts = gTTS(text=str('Chcecie usłyszeć fraszkę? Damian Damian ty huju.'), lang=language, slow=False)
    with open('fraszka1.mp3', 'wb') as f:
        tts.write_to_fp(f)
    tts2 = gTTS(text=str('Chcecie usłyszeć fraszkę? Służba zdrowia, wielki obszar, o którym można bardzo dugo mówić emmm prawda we fraszce Kochanowskiego "Szlachetne zdrowie" emm prawda "ile cię trzeba cenić" czy jak emm mmm tak emm "jako smakujesz, aż się zepsujesz" prawda i wtedy dopiero wiemy, kiedy brakuje nam tego zdrowia, emmm jak ono jest absolutnie kluczowe.'), lang=language, slow=False)
    with open('fraszka2.mp3', 'wb') as f:
        tts2.write_to_fp(f)
    tts3 = gTTS(text=str('Chcecie usłyszeć fraszkę? Viego co porucha to jego.'), lang=language, slow=False)
    with open('fraszka3.mp3', 'wb') as f:
        tts3.write_to_fp(f)
    tts4 = gTTS(text=str('Chcecie usłyszeć fraszkę? Tylko czerep nosi beret.'), lang=language, slow=False)
    with open('fraszka4.mp3', 'wb') as f:
        tts4.write_to_fp(f)
    tts5 = gTTS(text=str('Chcecie usłyszeć fraszkę? Miodek Miodek kiedy remix'), lang=language, slow=False)
    with open('fraszka5.mp3', 'wb') as f:
        tts5.write_to_fp(f)
    tts6 = gTTS(text=str('Sroga sroga to wielki obszar'), lang=language, slow=False)
    with open('fraszka6.mp3', 'wb') as f:
        tts5.write_to_fp(f)
    tts7 = gTTS(text=str('Jak damian zgankuje to nie ma hujwa we wsi'), lang=language, slow=False)
    with open('fraszka7.mp3', 'wb') as f:
        tts5.write_to_fp(f)
    tts8 = gTTS(text=str('Życie mnie mnie'), lang=language, slow=False)
    with open('fraszka8.mp3', 'wb') as f:
        tts5.write_to_fp(f)
    print(ktoramuzyka)
    if voice and voice.is_connected():
        await voice.move_to(channel)
        if ktoramuzyka == 1:
            voice.play(discord.FFmpegPCMAudio( source="fraszka1.mp3"))
            print('gram fraszke')
        if ktoramuzyka == 2:
            voice.play(discord.FFmpegPCMAudio( source="fraszka2.mp3"))
            print('gram fraszke 2')
        if ktoramuzyka == 3:
            voice.play(discord.FFmpegPCMAudio( source="fraszka3.mp3"))
            print('gram fraszke 3')
        if ktoramuzyka == 4:
            voice.play(discord.FFmpegPCMAudio( source="fraszka4.mp3"))
            print('gram fraszke 4')
        if ktoramuzyka == 5:
            voice.play(discord.FFmpegPCMAudio( source="fraszka5.mp3"))
            print('gram fraszke 5')
        if ktoramuzyka == 6:
            voice.play(discord.FFmpegPCMAudio( source="fraszka6.mp3"))
            print('gram fraszke 6')
        if ktoramuzyka == 7:
            voice.play(discord.FFmpegPCMAudio( source="fraszka7.mp3"))
            print('gram fraszke 7')
        if ktoramuzyka == 8:
            voice.play(discord.FFmpegPCMAudio( source="fraszka8.mp3"))
            print('gram fraszke 8')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        await voice.disconnect()
        print('wychodze')
    else:
        voice = await channel.connect()
        if ktoramuzyka == 1:
            voice.play(discord.FFmpegPCMAudio( source="fraszka1.mp3"))
            print('gram fraszke')
        if ktoramuzyka == 2:
            voice.play(discord.FFmpegPCMAudio( source="fraszka2.mp3"))
            print('gram fraszke 2')
        if ktoramuzyka == 3:
            voice.play(discord.FFmpegPCMAudio( source="fraszka3.mp3"))
            print('gram fraszke 3')
        if ktoramuzyka == 4:
            voice.play(discord.FFmpegPCMAudio( source="fraszka4.mp3"))
            print('gram fraszke 4')
        if ktoramuzyka == 5:
            voice.play(discord.FFmpegPCMAudio( source="fraszka5.mp3"))
            print('gram fraszke 5')
        if ktoramuzyka == 6:
            voice.play(discord.FFmpegPCMAudio( source="fraszka6.mp3"))
            print('gram fraszke 6')
        if ktoramuzyka == 7:
            voice.play(discord.FFmpegPCMAudio( source="fraszka7.mp3"))
            print('gram fraszke 7')
        if ktoramuzyka == 8:
            voice.play(discord.FFmpegPCMAudio( source="fraszka8.mp3"))
            print('gram fraszke 8')
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra')
        await voice.disconnect()
        print('wychodze')






@client.command()
async def play(ctx, url : str):

    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        voice.stop()
        await voice.move_to(channel)
        if os.path.exists('song.mp3'):
            os.remove('song.mp3')
        await asyncio.sleep(0.1)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        await asyncio.sleep(0.1)
        voice.play(discord.FFmpegPCMAudio( source="song.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze')
        os.remove('song.mp3')
    else:
        voice = await channel.connect()
        if os.path.exists('song.mp3'):
            os.remove('song.mp3')
        await asyncio.sleep(0.1)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        await asyncio.sleep(0.1)
        voice.play(discord.FFmpegPCMAudio( source="song.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze')
        os.remove('song.mp3')





@client.command()
async def play2(ctx, url : str):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    voice = await channel.connect()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url ,download=False)
        URL1 = info['url']
    voice.play(discord.FFmpegPCMAudio(source=URL1, **FFMPEG_OPTIONS))
    while voice.is_playing():
        await asyncio.sleep(2)
    await voice.disconnect()
    print('wychodze')

@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def pv(ctx, member: discord.Member):
    messagetext = ctx.message.clean_content
    final3text = messagetext.replace('cody!pv','')
    final2text = final3text.replace(member.name,'')
    finaltext4 = final2text.replace('@','')
    await ctx.message.delete()
    if member.nick is not None:
        final5text = finaltext4.replace(member.nick,'')
        finaltext = final5text
    else:
        finaltext = finaltext4
    await member.send(finaltext)
    await ctx.message.delete()


@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def spam(ctx, member: discord.Member):
    if not member.id == 264079253757231104:
        messagetext = ctx.message.clean_content
        final3text = messagetext.replace('cody!spam','')
        final2text = final3text.replace(member.name,'')
        finaltext4 = final2text.replace('@','')
        await ctx.message.delete()
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)

        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        await asyncio.sleep(2)
        if member.nick is not None:
            final5text = finaltext4.replace(member.nick,'')
            finaltext = final5text
        else:
            finaltext = finaltext4
        await member.send(finaltext)
        print("zaspamiony !!!!!!!!!!!!!!!!!!!!!!!!!--------------------------------------------------------------------------------------------------------")
        await ctx.message.delete()
    else:
        await ctx.author.send("otóż nie jak śmiesz używać moich zaklęć przeciwko mnie!")

@client.command()
async def joebiden(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="joebiden.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="joebiden.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def widziszmnie(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="widziszmnie.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="widziszmnie.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
@client.command()
async def gowno(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="gowno.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="gowno.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def stop(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    voice.stop()
    await asyncio.sleep(1)
    voice.play(discord.FFmpegPCMAudio( source="adiosleave.mp3"))
    print('gram leave')
    while voice.is_playing():
        await asyncio.sleep(4)
        print('gra')
    print('zastopowana')

@client.command()
async def wagary(ctx):
    member = ctx.message.author
    var = discord.utils.get(ctx.message.guild.roles, name = "wagary")
    await member.add_roles(var)
    embed = discord.Embed(title="WAGARY!", description=member.display_name + ' Jest od teraz na wagarach!') #,color=Hex code
    await ctx.send(embed=embed)
    await ctx.message.delete()


@client.command()
async def powagarach(ctx):
    member = ctx.message.author
    var = discord.utils.get(ctx.message.guild.roles, name = "wagary")
    await member.remove_roles(var)
    embed = discord.Embed(title="PO WAGARACH!", description=member.display_name + ' Już nie jest na wagarach!') #,color=Hex code
    await ctx.send(embed=embed)
    await ctx.message.delete()

@client.command()
async def walka(ctx, member: discord.Member):
    language = 'pl'
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    damage = randint(10, 50)
    autor = 100
    player2 = 100
    print(damage)


    tts = gTTS(text=str('Dobry wieczór. Witam na walce wieczoru.' + ctx.message.author.display_name + 'będzie dziś walczyć z. ' + member.display_name + '.Pojedynek na śmierć i życie.'), lang=language, slow=False)
    with open('walkastart.mp3', 'wb') as f:
        tts.write_to_fp(f)

    voice = await channel.connect()
    voice.play(discord.FFmpegPCMAudio( source="walkastart.mp3"))
    print('gram walka start')
    while voice.is_playing():
        await asyncio.sleep(1)
        print('gra')
    voice.stop()



    ttsd = gTTS(text=str(ctx.message.author.display_name) + '.Rozpoczyna atak zadając.' + str(damage) + '.' +'.damage.', lang=language, slow=False)
    with open('damage1.mp3', 'wb') as f:
        ttsd.write_to_fp(f)

    voice.play(discord.FFmpegPCMAudio( source="damage1.mp3"))
    while voice.is_playing():
        await asyncio.sleep(1)
        print('gra')
    wynik = player2 - damage
    player2 = wynik
    print(str(damage) + ' damage')
    print(str(player2) + ' player2')
    print(str(wynik) + ' wynik')
    damage = randint(10, 50)
    print(str(damage) + ' damage')



    if  player2 > 0 and autor > 0:
        voice.stop()
        ttsd2 = gTTS(text=member.display_name + '.odpowiada zadając.' + str(damage) + '.' +'.damage.', lang=language, slow=False)
        with open('damage2.mp3', 'wb') as f:
            ttsd2.write_to_fp(f)

        voice.play(discord.FFmpegPCMAudio( source="damage2.mp3"))
        while voice.is_playing():
            await asyncio.sleep(1)
            print('gra')
        wynik = autor - damage
        autor = wynik
        print(str(damage) + ' damage')
        print(str(autor) + ' player1')
        print(str(wynik) + ' wynik')
        damage = randint(10, 50)
        print(str(damage) + ' damage')
    if  player2 > 0 and autor > 0:
        voice.stop()
        ttsd3 = gTTS(text=str(ctx.message.author.display_name) + '.Nakurwia.' + str(damage) + '.' +'.damage.', lang=language, slow=False)
        with open('damage3.mp3', 'wb') as f:
            ttsd3.write_to_fp(f)

        voice.play(discord.FFmpegPCMAudio( source="damage3.mp3"))
        while voice.is_playing():
            await asyncio.sleep(1)
            print('gra')
        wynik = player2 - damage
        player2 = wynik
        print(str(damage) + ' damage')
        print(str(player2) + ' player2')
        print(str(wynik) + ' wynik')
        damage = randint(10, 50)
        print(str(damage) + ' damage')
    if  player2 > 0 and autor > 0:
        voice.stop()
        ttsd2 = gTTS(text=member.display_name + '. wykurwił.' + str(damage) + '.' +'.damage.', lang=language, slow=False)
        with open('damage2.mp3', 'wb') as f:
            ttsd2.write_to_fp(f)

        voice.play(discord.FFmpegPCMAudio( source="damage2.mp3"))
        while voice.is_playing():
            await asyncio.sleep(1)
            print('gra')
        wynik = autor - damage
        autor = wynik
        print(str(damage) + ' damage')
        print(str(autor) + ' player1')
        print(str(wynik) + ' wynik')
        damage = randint(10, 50)
        print(str(damage) + ' damage')
    if  player2 > 0 and autor > 0:
        voice.stop()
        ttsd3 = gTTS(text=str(ctx.message.author.display_name) + '. pierdoli.' + str(damage) + '.' +'.damage. aż się zesrałem', lang=language, slow=False)
        with open('damage3.mp3', 'wb') as f:
            ttsd3.write_to_fp(f)

        voice.play(discord.FFmpegPCMAudio( source="damage3.mp3"))
        while voice.is_playing():
            await asyncio.sleep(1)
            print('gra')
        wynik = player2 - damage
        player2 = wynik
        print(str(damage) + ' damage')
        print(str(player2) + ' player2')
        print(str(wynik) + ' wynik')
        damage = randint(10, 50)
        print(str(damage) + ' damage')

    if  player2 > 0 and autor > 0:
        voice.stop()
        ttsd2 = gTTS(text=member.display_name + '. zadaje obrażenia wynoszące 1 damiana w domu. żartuje.' + str(damage) +'.' + '.damage.', lang=language, slow=False)
        with open('damage2.mp3', 'wb') as f:
            ttsd2.write_to_fp(f)

        voice.play(discord.FFmpegPCMAudio( source="damage2.mp3"))
        while voice.is_playing():
            await asyncio.sleep(1)
            print('gra')
        wynik = autor - damage
        autor = wynik
        print(str(damage) + ' damage')
        print(str(autor) + ' player1')
        print(str(wynik) + ' wynik')
        damage = randint(10, 50)
        print(str(damage) + ' damage')

    if  player2 > 0 and autor > 0:
        voice.stop()
        ttsd3 = gTTS(text=str(ctx.message.author.display_name) + '. ale to było dobre.' + str(damage) +'.' + '.damage. aż się zesrałem', lang=language, slow=False)
        with open('damage3.mp3', 'wb') as f:
            ttsd3.write_to_fp(f)

        voice.play(discord.FFmpegPCMAudio( source="damage3.mp3"))
        while voice.is_playing():
            await asyncio.sleep(1)
            print('gra')
        wynik = player2 - damage
        player2 = wynik
        print(str(damage) + ' damage')
        print(str(player2) + ' player2')
        print(str(wynik) + ' wynik')
        damage = randint(10, 50)
        print(str(damage) + ' damage')
    if  player2 > 0 and autor > 0:
        voice.stop()
        ttsd2 = gTTS(text=member.display_name + '. ale urwał.' + str(damage) +'.' + '.damage.', lang=language, slow=False)
        with open('damage2.mp3', 'wb') as f:
            ttsd2.write_to_fp(f)

        voice.play(discord.FFmpegPCMAudio( source="damage2.mp3"))
        while voice.is_playing():
            await asyncio.sleep(1)
            print('gra')
        wynik = autor - damage
        autor = wynik
        print(str(damage) + ' damage')
        print(str(autor) + ' player1')
        print(str(wynik) + ' wynik')
        damage = randint(10, 50)
        print(str(damage) + ' damage')
    if  player2 > 0 and autor > 0:
        voice.stop()
        ttsd3 = gTTS(text=str(ctx.message.author.display_name) + '. zajebał.' + str(damage) +'.' + '.damage. aż się zesrałem', lang=language, slow=False)
        with open('damage3.mp3', 'wb') as f:
            ttsd3.write_to_fp(f)

        voice.play(discord.FFmpegPCMAudio( source="damage3.mp3"))
        while voice.is_playing():
            await asyncio.sleep(1)
            print('gra')
        wynik = player2 - damage
        player2 = wynik
        print(str(damage) + ' damage')
        print(str(player2) + ' player2')
        print(str(wynik) + ' wynik')
        damage = randint(10, 50)
        print(str(damage) + ' damage')
    if  player2 > 0 and autor > 0:
        voice.stop()
        ttsd2 = gTTS(text=member.display_name + '. zrobił lewy sierpowy wynoszący.' + str(damage) + '.' +'.damage.', lang=language, slow=False)
        with open('damage2.mp3', 'wb') as f:
            ttsd2.write_to_fp(f)

        voice.play(discord.FFmpegPCMAudio( source="damage2.mp3"))
        while voice.is_playing():
            await asyncio.sleep(1)
            print('gra')
        wynik = autor - damage
        autor = wynik
        print(str(damage) + ' damage')
        print(str(autor) + ' player1')
        print(str(wynik) + ' wynik')
        damage = randint(10, 50)
        print(str(damage) + ' damage')
    if  player2 > 0 and autor > 0:
        voice.stop()
        ttsd3 = gTTS(text=str(ctx.message.author.display_name) + '. łakamakafon.' + str(damage) + '.' + '.damage. No poszło', lang=language, slow=False)
        with open('damage3.mp3', 'wb') as f:
            ttsd3.write_to_fp(f)

        voice.play(discord.FFmpegPCMAudio( source="damage3.mp3"))
        while voice.is_playing():
            await asyncio.sleep(1)
            print('gra')
        wynik = player2 - damage
        player2 = wynik
        print(str(damage) + ' damage')
        print(str(player2) + ' player2')
        print(str(wynik) + ' wynik')
        damage = randint(10, 50)
        print(str(damage) + ' damage')














    if  not player2 > 0:
         voice.stop()
         ttswin2 = gTTS(text=str(ctx.message.author.display_name) + '. wygrał pojednynek. gratulacje', lang=language, slow=False)
         with open('win2tts.mp3', 'wb') as f:
             ttswin2.write_to_fp(f)

         voice.play(discord.FFmpegPCMAudio( source="win2tts.mp3"))
         while voice.is_playing():
             await asyncio.sleep(1)
             print('gra')

    if not autor > 0:
         voice.stop()
         ttswin = gTTS(text=str(member.display_name) + '. wygrał pojednynek. gratulacje', lang=language, slow=False)
         with open('wintts.mp3', 'wb') as f:
             ttswin.write_to_fp(f)

         voice.play(discord.FFmpegPCMAudio( source="wintts.mp3"))
         while voice.is_playing():
             await asyncio.sleep(1)
             print('gra')

    if  autor < 0 and player2 < 0:
         voice.stop()
         ttsren = gTTS(text= '. Remis Gratulacje X. D. ', lang=language, slow=False)
         with open('remistss.mp3', 'wb') as f:
             ttsren.write_to_fp(f)

         voice.play(discord.FFmpegPCMAudio( source="remistss.mp3"))
         while voice.is_playing():
             await asyncio.sleep(1)
             print('gra')
    voice.stop()
    voice.play(discord.FFmpegPCMAudio( source="congrats.mp3"))
    while voice.is_playing():
        await asyncio.sleep(1)
        print('gra')
    await ctx.voice_client.disconnect()
    print('wychodze!')



@client.command()
async def mial(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="mial.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="mial.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')


@client.command()
async def listawagarów(ctx):
    global wagarymembers
    hell = discord.utils.find(lambda r: r.name == 'wagary', ctx.guild.roles)

    await ctx.message.delete()
    for guild in client.guilds:
            for member in ctx.guild.members:
                if not member.display_name in wagarymembers:
                    if hell in member.roles:
                        wagarymembers.append(member.display_name)
                        print(wagarymembers)
    wagarymembers.sort()
    wfinaltext = str(wagarymembers).replace('[','')
    wfinaltext2 = str(wfinaltext).replace(']','')
    wfinaltext3 = str(wfinaltext2).replace("'",'')
    wfinaltext4 = str(wfinaltext3).replace(",",', \n')
    print(wfinaltext4)
    embed = discord.Embed(title="Aktualnie na wagarach!", description= wfinaltext4) #,color=Hex code
    await ctx.send(embed=embed)
    wagarymembers = []


@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def brazylia(ctx, member: discord.Member):
    channel = member.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    await asyncio.sleep(2)
    obywatel = member
    await asyncio.sleep(2)
    voice = await channel.connect()
    await ctx.message.delete()
    voice.play(discord.FFmpegPCMAudio( source="brazil.mp3"))
    await asyncio.sleep(3.7)
    await member.edit(voice_channel= None)
    var = discord.utils.get(ctx.message.guild.roles, name = "PszczelarzHell")
    await member.add_roles(var)
    while voice.is_playing():
        print('gra')
        await asyncio.sleep(2)
    await voice.disconnect()
    print('wychodze!!!')



@client.command()
async def syrena(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="syrena.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="syrena.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')




@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def alladdrole(ctx, role: discord.Role):
    if ctx.message.author.id == 264079253757231104:
        await ctx.message.add_reaction('✅')
        for guild in client.guilds:
            for member in ctx.guild.members:
                if not role in member.roles:
                    if member.bot == False:
                        await member.add_roles(role)
                        print('daje range')

@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def allremoverole(ctx, role: discord.Role):
    if ctx.message.author.id == 264079253757231104:
        await ctx.message.add_reaction('✅')
        for guild in client.guilds:
            for member in ctx.guild.members:
                if role in member.roles:
                    if member.bot == False:
                        await member.remove_roles(role)
                        print('usuwam range')

@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def quizjablon(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    global currentmember
    global kod2
    global quizmembers
    global czywygrana
    global damianvalue
    global czyktoswpisaldamian
    ktoramuzyka = 1
    value = randint(1, 20)
    if value == 1:
        kod2 = "atyjesteśkurwąspokojnąjakkostkalodutak"
    if value == 2:
        kod2 = "jajestemkurwomkurwomichujem"
    if value == 3:
        kod2 = "jasiekurwazaszczepiełebodpierdolebagnetemmoim"
    if value == 4:
        kod2 = "kurwa"
    if value == 5:
        kod2 = "myzomowcykurwatakiebutynosiliśmynapierdalaliśmywas"
    if value == 6:
        kod2 = "niepierdolniemożebyćcimiło"
    if value == 7:
        kod2 = "notosiękurwaniezniżajtosiępodnieśdogóry"
    if value == 8:
        kod2 = "oczymtychceszkurwadyskutować"
    if value == 9:
        kod2 = "pierdoleciękurwacotycowcograszwcograszteraz"
    if value == 10:
        kod2 = "poszołwondobudy"
    if value == 11:
        kod2 = "skurwysynutyzdychaj"
    if value == 12:
        kod2 = "stareskurwysynyjesteśmyjesteśmystarechuje"
    if value == 13:
        kod2 = "topochujtudzwonisz"
    if value == 14:
        kod2 = "towypierdalaj"
    if value == 15:
        kod2 = "wdupiemamprzykro"
    if value == 16:
        kod2 = "wieszżecizajebiekurwazbaniaka"
    if value == 17:
        kod2 = "wkurwiamnieto"
    if value == 18:
        kod2 = "wymordowaćwszystkichpolaków"
    if value == 19:
        kod2 = "wyrwecikurwoserce"
    if value == 20:
        kod2 = "zaszczepsięzdychaj"
    await asyncio.sleep(2)
    voice = await channel.connect()
    voice.play(discord.FFmpegPCMAudio( source=f"intro gdy wchodzijablon.mp3"))
    print('Uruchomiono quiz jablon!')
    await asyncio.sleep(27.1)
    voice.stop()
    for member in channel.members:
        if not member.id == 814510016433356834:
            await member.edit(mute=True)
            print('zmutowano go ^')


    currentmembers = channel.members
    quizmembers = channel.members
    await asyncio.sleep(0.1)
    voice.play(discord.FFmpegPCMAudio( source="przywitaniejablon.mp3"))
    for member in channel.members:
        if member.bot == True:
            if member in quizmembers:
                quizmembers.remove(member)


    await asyncio.sleep(0.1)
    print(kod2)
    print(damianvalue)
    print(ktoramuzyka)
    await asyncio.sleep(7.1)
    voice.stop()
    if value == 1:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="a ty jestes kurwą spokojną jak kostka lodu tak.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 2:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="ja jestem kurwom kurwom i chujem.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 3:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="ja sie kurwa zaszczepie łeb odpierdole bagnetem moim.mp3"))
        ktoramuzyka = 9
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 4:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="kurwa.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 5:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="my zomowcy kurwa takie buty nosiliśmy napierdalaliśmy was.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 6:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="nie pierdol nie może być ci miło.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 7:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="no to się kurwa nie zniżaj to się podnieś do góry.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 8:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="o czym ty chcesz kurwa dyskutować.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 9:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="pierdole cię kurwa co ty w co grasz w co grasz teraz.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')


    if value == 10:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="poszoł won do budy.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 11:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="skurwysynu ty zdychaj.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 12:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="stare skurwysyny jesteśmy jesteśmy stare huje.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 13:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="to po huj tu dzwonisz.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 14:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="to wypierdalaj.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 15:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="w dupie mam przykro.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 16:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="wieszżecizajebiekurwazbaniaka.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')

    if value == 17:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="wkurwiamnieto.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')
    if value == 18:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="wymordowaćwszystkichpolaków.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')
    if value == 19:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="wyrwecikurwoserce.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')
    if value == 20:
        voice.stop()
        voice.play(discord.FFmpegPCMAudio( source="zaszczepsięzdychaj.mp3"))
        while voice.is_playing():
            await asyncio.sleep(2)
            print('gra pytanie')


    voice.stop()
    if ktoramuzyka == 1:
        voice.play(discord.FFmpegPCMAudio( source="muzykanawpisywaniekodujablon.mp3"))
        print('gram muzykanawpisywaniekodujablon')
    while voice.is_playing():
        await asyncio.sleep(2)
        print('gra quiz')
        if len(quizmembers) == 0:
            voice.stop()
            await asyncio.sleep(0.1)
            if czyktoswpisaldamian == 1:
                voice.play(discord.FFmpegPCMAudio( source="pedal.mp3"))
                czywygrana = 1
                await asyncio.sleep(3)
            else:
                voice.play(discord.FFmpegPCMAudio( source="quizudanyjb.mp3"))
                czywygrana = 1
                await asyncio.sleep(2.8)


    if czywygrana is None:
        voice.play(discord.FFmpegPCMAudio( source="wywalaniejablon.mp3"))

    await asyncio.sleep(2)
    for member in channel.members:
            await member.edit(mute=False)
    await asyncio.sleep(2)
    for member in channel.members:
        if member in quizmembers:
            quizmembers.remove(member)
            await member.edit(voice_channel= None)
            hell = discord.utils.find(lambda r: r.name == 'PszczelarzHell', ctx.guild.roles)
            if not hell in member.roles:
                if member.bot == False:
                    await member.add_roles(hell)
                    print('dano range')


    await asyncio.sleep(2)
    czywygrana = None
    damianvalue = None
    czyktoswpisaldamian = None
    await voice.disconnect()

@client.command()
@has_permissions(kick_members=True, ban_members=True)
async def ankieta(ctx, *, message=None):

        if message == None:
                await ctx.send(f'Ale że bez niczego we jeszcze raz!')
                return

        questions = [
            f"Na jaki kanał wysłać wariacie?"
        ]
        answers = []

        def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

        for i in questions:
                await ctx.send(i)

                try:

                      msg = await client.wait_for('message', timeout=30.0, check=check)

                except asyncio.TimeoutError:
                        await ctx.send("Od nowa tylko szybciej zateguj!")
                        return
                else:
                        answers.append(msg.content)

        try:
                c_id = int(answers[0][2:-1])
        except:
                await ctx.send(
                    f"Nie wybrałeś kanału we tam zatguj na przykład {ctx.channel.mention} następnym razem."
                )
                return

        channel = client.get_channel(c_id)

        rolep = discord.utils.get(ctx.message.author.guild.roles, name="Ankietowicze")
        embed = discord.Embed(title="Ankieta", description= message + '\n' + 'Macie 10 minut na odpowiedź!', colour=discord.Color.purple())
        ping = await channel.send(rolep.mention)
        message = await channel.send(embed=embed)
        await message.add_reaction('👍')
        await message.add_reaction('👎')
        await asyncio.sleep(1)
        cache_message = discord.utils.get(client.cached_messages, id=message.id) #or client.messages depending on your variable
        print(cache_message.reactions)
        await asyncio.sleep(599)
        reaction1 = get(cache_message.reactions, emoji='👍')
        print(reaction1)
        reaction2 = get(cache_message.reactions, emoji='👎')
        print(reaction2)
        if reaction1.count > reaction2.count:
            embed = discord.Embed(title="Ankieta", description='Wygrała odpowiedź 👍 mając '+ str(reaction1.count) + ' głosy. Gratuluje! ', colour=discord.Color.purple())
            message2 = await channel.send(embed=embed)
        if reaction2.count > reaction1.count:
            embed = discord.Embed(title="Ankieta", description='Wygrała odpowiedź 👎 mając '+ str(reaction2.count) + ' głosy. Gratuluje! ', colour=discord.Color.purple())
            message3 = await channel.send(embed=embed)
        if reaction2.count == reaction1.count:
            embed = discord.Embed(title="Ankieta", description='Remis!!!!!!!!🤔', colour=discord.Color.purple())
            message4 = await channel.send(embed=embed)


@client.command()
async def orzel(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="orzel.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="orzel.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def order66p2(ctx):
    global order66val
    if ctx.message.author.id == 264079253757231104:
        await ctx.message.add_reaction('✅')
        embed = discord.Embed(title="Rozkaz 66", description= "Imperator zadecydował w związku z rozkazem 66, że każdy za nawet najmniejsze przewienienie zostanie wtrącony do gułagu!") #,color=Hex code
        await ctx.send(embed=embed)
        await ctx.message.delete()
        order66val = 1

    else:
        print('to nie kubadi')
        language = 'pl'
        await ctx.message.add_reaction('❌')


@client.command()
async def godzinapolicyjna(ctx):
    global godzinapol
    if ctx.message.author.id == 264079253757231104:
        await ctx.message.add_reaction('✅')
        embed = discord.Embed(title="Godzina Policyjna!", description= "Imperator zadecydował w związku z pogarszeniem się sytuacji w państwie na rutynowe kontrole policji.") #,color=Hex code
        await ctx.send(embed=embed)
        await ctx.message.delete()
        godzinapol = 1

    else:
        print('to nie kubadi')
        language = 'pl'
        await ctx.message.add_reaction('❌')

@client.command()
async def fixgodzinypol(ctx):
    global godzinapol
    global sprawdzanie
    if ctx.message.author.id == 264079253757231104:
        await ctx.message.add_reaction('✅')
        sprawdzanie = 0
        embed = discord.Embed(title="Godzina Policyjna!", description= "Naprawiono") #,color=Hex code
        await ctx.send(embed=embed)
        await ctx.message.delete()

    else:
        print('to nie kubadi')
        language = 'pl'
        await ctx.message.add_reaction('❌')

@client.command()
async def poorder66(ctx):
    global order66val
    if ctx.message.author.id == 264079253757231104:
        await ctx.message.add_reaction('✅')
        embed = discord.Embed(title="Po rozkazie 66", description= "Imperator zadecydował by znieść obostrzenia.") #,color=Hex code
        await ctx.send(embed=embed)
        await ctx.message.delete()
        order66val = 0

    else:
        print('to nie kubadi')
        language = 'pl'
        await ctx.message.add_reaction('❌')

@client.command()
async def pogodziniepolicyjnej(ctx):
    global godzinapol
    if ctx.message.author.id == 264079253757231104:
        await ctx.message.add_reaction('✅')
        embed = discord.Embed(title="Po godzinie policyjnej!", description= "Imperator zadecydował by znieść obostrzenia.") #,color=Hex code
        await ctx.send(embed=embed)
        await ctx.message.delete()
        godzinapol = 0

    else:
        print('to nie kubadi')
        language = 'pl'
        await ctx.message.add_reaction('❌')

@client.command()
async def demacia(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="demacia.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="demacia.mp3"))
        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')

@client.command()
async def demacia2(ctx, member: discord.Member):
    channel = member.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():

        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="demacia.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')
    else:

        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="demacia.mp3"))

        await ctx.message.delete()
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        print('wychodze!!!')


@client.command(pass_context=True)
async def tajnykanalpabianickiejmafii(ctx):
    member = ctx.message.author
    hell = discord.utils.find(lambda r: r.name == '🌹Pabianicka Mafia', ctx.guild.roles)
    if hell in member.roles:
            primary_id = str(ctx.message.author.id)
            embed = discord.Embed(title="🌹Uwaga Pabianicka Mafia ma tajne zgromadzenie!🌹", description= ' Uważajcie na siebie. Pozdrawiamy Pabianicka Mafia.', colour=discord.Color.red())
            embed.set_thumbnail(url = 'https://i.ytimg.com/vi/zN7qD6GoiK4/maxresdefault.jpg')
            message4 = await ctx.send(embed=embed)
            guild = ctx.guild
            mafia_role = get(guild.roles, name="🌹Pabianicka Mafia")
            user_role = get(guild.roles, name="🎮Gamer")
            await ctx.message.delete()
            guild = ctx.message.guild
            cat = discord.utils.get(ctx.guild.categories, name="🔊 GADANIE")
            overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            mafia_role: discord.PermissionOverwrite(read_messages=True),
            mafia_role: discord.PermissionOverwrite(manage_channels=True),
            user_role: discord.PermissionOverwrite(read_messages=False)

            }
            channel2 = await guild.create_voice_channel("🌹Spotkanie Mafii Pabianickiej", category=cat, overwrites=overwrites)
            channel = channel2
            voice = get(client.voice_clients, guild=ctx.guild)
            if voice and voice.is_connected():
                await voice.move_to(channel)
                voice.play(discord.FFmpegPCMAudio( source="mafia.mp3"))
                print('Gram mafia')
                while voice.is_playing():
                    print('gra')
                    await asyncio.sleep(2)
                await voice.disconnect()
            else:
                voice = await channel.connect()
                voice.play(discord.FFmpegPCMAudio( source="mafia.mp3"))
                print('Gram mafia')
                while voice.is_playing():
                    print('gra')
                    await asyncio.sleep(2)
                await voice.disconnect()


@client.command()
async def zastrzel(ctx, member: discord.Member):
    member2 = ctx.message.author
    hell = discord.utils.find(lambda r: r.name == '🌹Pabianicka Mafia', ctx.guild.roles)
    if hell in member2.roles:
        channel = member.voice.channel
        voice = get(client.voice_clients, guild=ctx.guild)
        language = 'pl'
        tts = gTTS(text=str('Witam cię '+ (member.name)+ ' jak widzisz pabianicka mafia właśnie cię dopadła'), lang=language, slow=False)
        with open('egzekucja.mp3', 'wb') as f:
            tts.write_to_fp(f)
        await asyncio.sleep(1)
        obywatel = member
        if not obywatel.id == 264079253757231104 and not obywatel.id == 243024515141992450:
            voice = await channel.connect()
            print(obywatel)
            await asyncio.sleep(0.5)
            print(obywatel)
            voice.play(discord.FFmpegPCMAudio( source="egzekucja.mp3"))
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(1)
            voice.stop()
            voice.play(discord.FFmpegPCMAudio( source="shotgun.mp3"))
            await asyncio.sleep(3)
            await obywatel.edit(voice_channel= None)
            await asyncio.sleep(2)
            print('wywalono ' + (obywatel.name))
            await ctx.message.delete()
            await voice.disconnect()
        else:
            print('On chce zajebac prezydenta!')
            language = 'pl'
            await ctx.message.add_reaction('❌')
            voice = await channel.connect()
            tts = gTTS(text=str(ctx.message.author.name) + ' A co to za zamach?', lang=language, slow=False)
            with open('perm.mp3', 'wb') as f:
                tts.write_to_fp(f)
            voice.play(discord.FFmpegPCMAudio( source="perm.mp3"))
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            voice.play(discord.FFmpegPCMAudio( source="shotgun.mp3"))
            await asyncio.sleep(3)
            await ctx.message.author.edit(voice_channel= None)
            await asyncio.sleep(2)
            await voice.disconnect()
            await ctx.message.delete()


@client.command()
async def pabianickamafia(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="mafia.mp3"))
        print('Gram mafia')
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="mafia.mp3"))
        print('Gram mafia')
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()

@client.command()
async def herbata(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    language = 'pl'
    tts = gTTS(text=str('Wnuczku. chcesz herbate?'), lang=language, slow=False)
    with open('herbata.mp3', 'wb') as f:
        tts.write_to_fp(f)
    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="herbata.mp3"))
        print('Gram mafia')
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="herbata.mp3"))
        print('Gram mafia')
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
    await asyncio.sleep(300)

    voice = get(client.voice_clients, guild=ctx.guild)
    tts = gTTS(text=str('Wnuczku. chcesz herbate?'), lang=language, slow=False)
    with open('herbata.mp3', 'wb') as f:
        tts.write_to_fp(f)
    if voice and voice.is_connected():
        await voice.move_to(channel)
        voice.play(discord.FFmpegPCMAudio( source="herbata.mp3"))
        print('Gram mafia')
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
    else:
        voice = await channel.connect()
        voice.play(discord.FFmpegPCMAudio( source="herbata.mp3"))
        print('Gram mafia')
        while voice.is_playing():
            print('gra')
            await asyncio.sleep(2)
        await voice.disconnect()
        await asyncio.sleep(300)

        voice = get(client.voice_clients, guild=ctx.guild)
        tts = gTTS(text=str('Wnuczku. chcesz herbate?'), lang=language, slow=False)
        with open('herbata.mp3', 'wb') as f:
            tts.write_to_fp(f)
        if voice and voice.is_connected():
            await voice.move_to(channel)
            voice.play(discord.FFmpegPCMAudio( source="herbata.mp3"))
            print('Gram mafia')
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            await voice.disconnect()
        else:
            voice = await channel.connect()
            voice.play(discord.FFmpegPCMAudio( source="herbata.mp3"))
            print('Gram mafia')
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            await voice.disconnect()
            await asyncio.sleep(300)

            voice = get(client.voice_clients, guild=ctx.guild)
            tts = gTTS(text=str('Wnuczku. chcesz herbate?'), lang=language, slow=False)
            with open('herbata.mp3', 'wb') as f:
                tts.write_to_fp(f)
            if voice and voice.is_connected():
                await voice.move_to(channel)
                voice.play(discord.FFmpegPCMAudio( source="herbata.mp3"))
                print('Gram mafia')
                while voice.is_playing():
                    print('gra')
                    await asyncio.sleep(2)
                await voice.disconnect()
            else:
                voice = await channel.connect()
                voice.play(discord.FFmpegPCMAudio( source="herbata.mp3"))
                print('Gram mafia')
                while voice.is_playing():
                    print('gra')
                    await asyncio.sleep(2)
                await voice.disconnect()

client.run(os.environ['PszczelarzBOT_TOKEN'])
