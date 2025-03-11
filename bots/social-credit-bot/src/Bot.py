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
from urllib.parse import urlparse
from difflib import SequenceMatcher
from PIL import Image
import imagehash
import requests

# Set working directory to one level up from where bot.py is
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(script_dir, "..")
os.chdir(parent_dir)  # Change working directory

print("Working directory set to:", os.getcwd())


gulagmembers = []
currentusernfts = []
HOSTNAME = os.environ['FTP_HOSTNAME']
USERNAME = os.environ['FTP_USERNAME']
PASSWORD = os.environ['FTP_PASSWORD']
base = 0
start = 0
start2 = 0
wywozi = 0
atakgosciu = None
atak = 0
atakczyprzeciwnik = 0
czyjuzuruchomiono = 0
czydalowyplate = 0
wywozyudane = 0
gryniedozwolone = ['genshin impact']
gracze = {}
graczewygrani = []
creditsocialimages = ['https://i.ytimg.com/vi/pq-koFphG0k/maxresdefault.jpg','https://i.ytimg.com/vi/1PIMW8pryOs/maxresdefault.jpg','https://video-images.vice.com/articles/61713cd171b09a0094c168dd/lede/1635139741537-img7084.jpeg','https://i.ytimg.com/vi/ZBDRIy4X2sU/maxresdefault.jpg','https://preview.redd.it/acd8kg6rxik71.png?auto=webp&s=d429c8ee33e08afe49b073f367de5cd7ca0ec98a','https://i.ytimg.com/vi/UNeDsyT3678/mqdefault.jpg','https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQPkwjo879dY0XoTq7FdHM8oLDphcJcNihduA&usqp=CAU']
creditplusimages = ['https://c.tenor.com/RvBPEdvCqHkAAAAd/social-credit.gif','https://c.tenor.com/LhFDiiL3dxwAAAAC/social-credit-sad-spongebob.gif','https://c.tenor.com/9r1rE1-uyFYAAAAd/social-credit.gif', 'https://i.pinimg.com/736x/8e/53/6e/8e536e4e6ab3603cd34055ef9e64bb83.jpg','https://starecat.com/content/wp-content/uploads/xi-jinping-bro-you-just-posted-cringe-you-are-going-to-lose-social-credit-points.jpg','https://i.ytimg.com/vi/0JRd1Fsgavw/maxresdefault.jpg']
nagrodamessage = ['Wykopałeś kartofle','Niestety wykopałeś gufno','Wykopałeś mózg <@290179026474106881>. Troche mały!','Gratulacje! Wykopałeś Prisoners Life 2!','Niestety wykopałeś anime','Gratulacje! Wykopałeś przejebane 200zł wiśniewskiego!','Niestety wykopałeś kartkówke z matmy miodka','Gratulacje! Wykopałeś komputer <@290179026474106881>!','Niestety wykopałeś dziwny post z czerepalni!','Gratulacje! Wykopałeś ukradzione konto fortnite czerepaka!','Niestety wykopałeś skina za 40gr!','Gratulacje! Wykopałeś MidasFisha!','Niestety wykopałeś zużyty złoty kod z keydropa!','Niestety wykopałeś dugana 0/10','Gratulacje! wykopałeś 20%z napadu!','Gratulacje! wykopałeś 20%z napadu!','Niestety wykopałeś obrazy! Rolluj dalej!','Gratulacje wykopałeś czerepaka z plebani!']
questchoose = ['Wykop 3 razy cos w kopalni','Zagraj i wygraj na ruletce','Kup pozdrowienia od Johna Xiny', 'Napisz h na ✍-h']
intents = discord.Intents.all()
client = commands.Bot(command_prefix='sc!',intents=intents)
status = cycle(['Chiny','to','fajny','kraj'])
@client.event
async def on_ready():
    change_status.start()
    print('SocialCreditBOT aktywowany!')
    print(str(datetime.datetime.now().time()))
    global amounts
    global base
    global quests
    global wytwornie
    global nfts
    global gulaggrzywna
    global nftowners
    try:
        # Connect FTP Server
        ftp_server = ftplib.FTP(HOSTNAME, USERNAME, PASSWORD)

        # force UTF-8 encoding
        ftp_server.encoding = "utf-8"
        # Get list of files
        ftp_server.cwd('htdocs')
        ftp_server.dir()
        # Enter File Name with Extension
        filename = "amounts.json"
        filename2 = "quests.json"
        filename3 = "wytwornie.json"
        filename4 = "grzywna.json"
        filename5 = "nfts.json"
        filename6 = "nftowners.json"
        # Write file in binary mode
        with open(filename, "wb") as file:
            # Command for Downloading the file "RETR filename"
            ftp_server.retrbinary(f"RETR {filename}", file.write)
            print('odebrano' + str({filename}))
        with open(filename3, "wb") as file3:
            # Command for Downloading the file "RETR filename"
            ftp_server.retrbinary(f"RETR {filename3}", file3.write)
            print('odebrano' + str({filename3}))
        with open(filename4, "wb") as file4:
            # Command for Downloading the file "RETR filename"
            ftp_server.retrbinary(f"RETR {filename4}", file4.write)
            print('odebrano' + str({filename4}))
        with open(filename5, "wb") as file5:
            # Command for Downloading the file "RETR filename"
            ftp_server.retrbinary(f"RETR {filename5}", file5.write)
            print('odebrano' + str({filename5}))
        with open(filename6, "wb") as file6:
            # Command for Downloading the file "RETR filename"
            ftp_server.retrbinary(f"RETR {filename6}", file6.write)
            print('odebrano' + str({filename6}))
        with open(filename2, "wb") as file2:
            # Command for Downloading the file "RETR filename"
            ftp_server.retrbinary(f"RETR {filename2}", file2.write)
            print('odebrano' + str({filename2}))
            base = 1
        await asyncio.sleep(1)
            # Read file in binary mode
        with open(filename, "rb") as file:
            # Command for Uploading the file "STOR filename"
            ftp_server.storbinary(f"STOR {filename}", file)
            print('wysyłano' + str({filename}))
        with open(filename2, "rb") as file2:
            # Command for Uploading the file "STOR filename"
            ftp_server.storbinary(f"STOR {filename2}", file2)
            print('wysyłano' + str({filename2}))
        with open(filename4, "rb") as file4:
            # Command for Uploading the file "STOR filename"
            ftp_server.storbinary(f"STOR {filename4}", file4)
            print('wysyłano' + str({filename4}))
        with open(filename5, "rb") as file5:
            # Command for Uploading the file "STOR filename"
            ftp_server.storbinary(f"STOR {filename5}", file5)
            print('wysyłano' + str({filename5}))
        with open(filename6, "rb") as file6:
            # Command for Uploading the file "STOR filename"
            ftp_server.storbinary(f"STOR {filename6}", file6)
            print('wysyłano' + str({filename6}))
        with open(filename3, "rb") as file3:
            # Command for Uploading the file "STOR filename"
            ftp_server.storbinary(f"STOR {filename3}", file3)
            print('wysyłano' + str({filename3}))
        # Close the Connection
        await asyncio.sleep(8)
        if base == 1:
            with open('amounts.json') as f:
                amounts = json.load(f)
                print("loaded amounts database")
            with open('grzywna.json') as h:
                gulaggrzywna = json.load(h)
                print("loaded gulag grzywna database")
            with open('quests.json') as d:
                quests = json.load(d)
                print("loaded quest database")
            with open('nfts.json') as k:
                nfts = json.load(k)
                print("loaded nfts database")
            with open('nftowners.json') as m:
                nftowners = json.load(m)
                print("loaded nftowners database")
            with open('wytwornie.json') as c:
                wytwornie = json.load(c)
                print("loaded wytwornie database")
                ftp_server.quit()
                change_kopanie.start()
                change_wyplata.start()
                change_pobieranie.start()
                print("zerwano połączenie ręcznie")
    except:
            print("Could not download data (maybe server is down?)")
            for guild in client.guilds:
               channel = get(guild.text_channels, name='spam')
               if channel is not None:
                  embed = discord.Embed(title="Serwer nie odpowiada ❌ ", description=' Użwyam lokalnych plików mogą być nie aktualne.', colour=discord.Color.dark_red())
                  embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/4675/4675793.png')
                  message = await channel.send(embed=embed)

            amounts = {}
            wytwornie = {}
            nfts = {}
            quests = {}
            nftowners = {}
            gulaggrzywna = {}
            with open('amounts.json') as f:
                amounts = json.load(f)
                print("loaded amounts database")
            with open('grzywna.json') as h:
                gulaggrzywna = json.load(h)
                print("loaded gulag grzywna database")
            with open('quests.json') as d:
                quests = json.load(d)
                print("loaded quest database")
            with open('nfts.json') as k:
                nfts = json.load(k)
                print("loaded nfts database")
            with open('nftowners.json') as m:
                nftowners = json.load(m)
                print("loaded nftowners database")
            with open('wytwornie.json') as c:
                wytwornie = json.load(c)
                print("loaded wytwornie database")
            change_kopanie.start()
            change_wyplata.start()
            change_pobieranie.start()


@client.command(pass_context=True)
async def saldo(ctx):
    id2 = str(ctx.message.author.id)
    id = id2 + ' kasa'
    if id in amounts:
        await ctx.send("Masz {} social credit w banku".format(amounts[id]))
    else:
        await ctx.send("Nie masz konta. zarejestruj sie sc!zarejestruj")


@client.command(pass_context=True)
async def gulaggrzywna(ctx):
    id2 = str(ctx.message.author.id)
    id = id2 + ' kasa'
    if id in amounts:
        await ctx.send("Masz {} social credit grzywny za wyjście z gułagu do zapłacenia!".format(gulaggrzywna[id]))
    else:
        await ctx.send("Nie masz konta.")



@client.command(pass_context=True)
async def quest(ctx):
    id2 = str(ctx.message.author.id)
    id = id2
    if id in quests:
        if not quests[id] == '':
            await ctx.send('Quest: '+ str(quests[id]) + ' ,postęp: '+str(quests[str(ctx.message.author.name)]))
        else:
            await ctx.send("Aktualnie nie masz żadnego questa. Wpisz sc!dajquest")


    else:
        await ctx.send("Nie brałeś nigdy questa by to sprawdzić")


@client.command(pass_context=True)
async def energia(ctx):
    id2 = str(ctx.message.author.id)
    id = id2 + ' awanturniczosc'
    if id in amounts:
        await ctx.send("Masz {} energii".format(amounts[id]))
    else:
        await ctx.send("Nie masz konta. zarejestruj sie sc!zarejestruj")

@client.command(pass_context=True)
async def zarejestruj(ctx):
    id = str(ctx.message.author.id)
    id2 = id + ' kasa'
    name = str(ctx.message.author.name)
    if id2 not in amounts:
        amounts[id + ' kasa'] = 100
        amounts[id + ' awanturniczosc'] = 100
        await ctx.send("Od teraz jesteś zarejestrowany!")
        _save()
        await asyncio.sleep(1)
        _upload()





@client.command(pass_context=True)
async def kupbunkier(ctx):
    amount = 1000
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    primary_id3 = primary_id2 + ' wytwornia'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        if str(primary_id2 + ' wytwornia rodzaj') in wytwornie:
            embed = discord.Embed(title="Już masz bunkier ❌ ", description=str(ctx.message.author.name)+ ' co ty chcesz!', colour=discord.Color.dark_red())
            embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
            message4 = await ctx.send(embed=embed)
            await ctx.message.delete()
        if str(primary_id2 + ' wytwornia rodzaj') not in wytwornie:
            wytwornie[primary_id3 + ' wywoz'] = 0
            wytwornie[primary_id3 + ' rodzaj'] = 'bunkier'
            wytwornie[primary_id3 + ' kasa'] = 0
            wytwornie[primary_id3 + ' napad'] = 0
            wytwornie[primary_id3 + ' ulepszenie'] = 0
            wytwornie[primary_id3 + ' zasoby'] = 0
            wytwornie[primary_id3 + ' skin'] = 0
            wytwornie[primary_id3 + ' amunicja'] = 0
            wytwornie[primary_id3 + ' pomieszczenie'] = ''
            wytwornie[primary_id3 + ' bron'] = ''
            wytwornie[primary_id3 + ' zolnierze'] = 0
            amounts[primary_id] -= amount
            embed = discord.Embed(title="Zakupiono Bunkier", description=str(ctx.message.author.display_name) + ' kupił Bunkier za ' + str(amount) + ' social credit!', colour=discord.Color.blue())
            embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
            message4 = await ctx.send(embed=embed)
            _save()
            await asyncio.sleep(1)
            _upload()
            await ctx.message.delete()




@client.command(pass_context=True)
async def bunkier(ctx):
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    primary_id3 = primary_id2 + ' wytwornia'
    await ctx.message.delete()
    if str(primary_id2 + ' wytwornia rodzaj') in wytwornie:
        if wytwornie[primary_id3 + ' rodzaj'] == 'bunkier':
            if wytwornie[primary_id3 + ' ulepszenie'] == 0 and wytwornie[primary_id3 + ' skin'] == 0 and wytwornie[primary_id3 + ' rodzaj'] == 'bunkier':
                kasa = wytwornie[primary_id3 + ' zasoby'] * 2
                embed = discord.Embed(title="Bunkier " + str(ctx.message.author.name), description= 'Zasoby: ' + str(wytwornie[primary_id3 + ' zasoby']) +' \n '+  'Wartość towaru: ' + str(kasa) + ' Social Credit' + ' \n ' + 'Łącznie zarobiono: ' + str(wytwornie[primary_id3 + ' kasa']) + ' Social Credit' + ' \n ' + 'Poziom: ' + str(wytwornie[primary_id3 + ' ulepszenie']), colour=discord.Color.dark_grey())
                embed.set_thumbnail(url = 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/OOjs_UI_icon_lock.svg/768px-OOjs_UI_icon_lock.svg.png')
                message4 = await ctx.send(embed=embed)
                await ctx.send(file=discord.File('bunkry//bunkierlvl0.jpg'))
        if wytwornie[primary_id3 + ' rodzaj'] == 'bimbrownia':
            if wytwornie[primary_id3 + ' ulepszenie'] == 0 and wytwornie[primary_id3 + ' skin'] == 0 and wytwornie[primary_id3 + ' rodzaj'] == 'bimbrownia':
                kasa = wytwornie[primary_id3 + ' zasoby'] * 2
                embed = discord.Embed(title="Bunkier " + str(ctx.message.author.name), description= 'Zasoby: ' + str(wytwornie[primary_id3 + ' zasoby']) +' \n '+  'Wartość towaru: ' + str(kasa) + ' Social Credit' + ' \n ' + 'Łącznie zarobiono: ' + str(wytwornie[primary_id3 + ' kasa']) + ' Social Credit' + ' \n ' + 'Poziom: ' + str(wytwornie[primary_id3 + ' ulepszenie']), colour=discord.Color.dark_grey())
                embed.set_thumbnail(url = 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/OOjs_UI_icon_lock.svg/768px-OOjs_UI_icon_lock.svg.png')
                message4 = await ctx.send(embed=embed)
                await ctx.send(file=discord.File('bunkry//bunkierlvl0.jpg'))


@client.command(pass_context=True)
async def wywoz(ctx):
    global wywozi
    global atakgosciu
    global atakczyprzeciwnik
    global atak
    global wywozyudane
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    primary_id3 = primary_id2 + ' wytwornia'

    if str(primary_id2 + ' wytwornia zasoby') in wytwornie:
        if wytwornie[primary_id3 + ' zasoby'] <= 0 and wywozi == 0:
            embed = discord.Embed(title="Nie można wywieść ❌ ", description=' Zasoby: '+ str(wytwornie[primary_id3 + ' zasoby']) , colour=discord.Color.dark_red())
            embed.set_thumbnail(url = 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/OOjs_UI_icon_lock.svg/768px-OOjs_UI_icon_lock.svg.png')
            message4 = await ctx.send(embed=embed)
            await ctx.message.delete()
        if wywozi == 1:
            embed = discord.Embed(title="Nie można wywieść ❌ ", description='Atualnie usługi transportowe są zajęte! ', colour=discord.Color.dark_red())
            embed.set_thumbnail(url = 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/OOjs_UI_icon_lock.svg/768px-OOjs_UI_icon_lock.svg.png')
            message4 = await ctx.send(embed=embed)
            await ctx.message.delete()
        if wytwornie[primary_id3 + ' zasoby'] >= 1 and wytwornie[primary_id3 + ' ulepszenie'] == 0 and wytwornie[primary_id3 + ' rodzaj'] == 'bunkier' and wytwornie[primary_id3 + ' wywoz'] == 0 and wywozi == 0:
            embed = discord.Embed(title="Wywozy u " + str(ctx.message.author.name) + str(' 🚚'), description=' Zasoby: '+ str(wytwornie[primary_id3 + ' zasoby']) + ' . Za 60 sekund dostarczymy' , colour=discord.Color.blue())
            embed.set_thumbnail(url = 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/OOjs_UI_icon_lock.svg/768px-OOjs_UI_icon_lock.svg.png')
            kasa = wytwornie[primary_id3 + ' zasoby'] * 2
            wytwornie[primary_id3 + ' wywoz'] = 60
            wywozi = 1
            await ctx.message.delete()
            _save()
            await asyncio.sleep(1)
            _upload()
            print(str(kasa))
            message4 = await ctx.send(embed=embed)
            await asyncio.sleep(2)
            while wytwornie[primary_id3 + ' wywoz'] > 0:
                print('jedzie')
                await asyncio.sleep(1)
                wywozyudane = 1
                atak = 0
                wytwornie[primary_id3 + ' wywoz'] -= 1
                _save()
                if atakgosciu is not None:
                    wywozyudane = 0
                    wytwornie[primary_id3 + ' wywoz'] = 0
                    przeciwnik = atakgosciu
                    print(przeciwnik)
                    atak = 1
                    wywozyudane = 0
            if atak == 1 and atakgosciu is not None:
                questions = [f"Atakują nas {ctx.author.mention} !!!!!!! szybko zareguj zanim nas dojadą i stracisz zasoby! Wpisz obron!! Masz 20 sekund zanim ukradną!"]
                answers = []
                def check(m):
                        return m.author == ctx.author and m.channel == ctx.channel and m.content == 'obron'
                for i in questions:
                        await ctx.send(i)
                        try:
                              msg = await client.wait_for('message', timeout=20.0, check=check)
                        except asyncio.TimeoutError:
                                embed = discord.Embed(title="Zasoby ukradzione ❌ ", description=str(atakgosciu.name)+ ' ukradł ci zasoby!', colour=discord.Color.dark_red())
                                embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/10/10925.png')
                                message4 = await ctx.send(embed=embed)
                                wytwornie[str(atakgosciu.id) + ' wytwornia zasoby'] += wytwornie[primary_id3 + ' zasoby']
                                wytwornie[primary_id3 + ' zasoby'] = 0
                                kasa = 0
                                atak = 0
                                wywozi = 0
                                atakgosciu = None
                                atakczyprzeciwnik = 0
                                wywozyudane = 0
                                wytwornie[primary_id3 + ' wywoz'] = 0
                                _save()
                                await asyncio.sleep(1)
                                _upload()
                                return
                        else:
                                answers.append(msg.content)
                                if 'obron' in answers or 'obroń' in answers or 'Obroń' in answers or 'Obron' in answers:
                                    wytwornie[primary_id3 + ' kasa'] += kasa
                                    amounts[primary_id] += kasa
                                    wytwornie[primary_id3 + ' zasoby'] = 0
                                    wytwornie[primary_id3 + ' wywoz'] = 0
                                    _save()
                                    await asyncio.sleep(1)
                                    _upload()
                                    embed = discord.Embed(title="Wywozy u " + str(ctx.message.author.name) + ' udane! 🚚', description=' Zarobiono: '+ str(kasa) + ' Social Credit!', colour=discord.Color.green())
                                    embed.set_thumbnail(url = 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/OOjs_UI_icon_lock.svg/768px-OOjs_UI_icon_lock.svg.png')
                                    message4 = await ctx.send(embed=embed)
                                    kasa = 0
                                    atak = 0
                                    wywozi = 0
                                    atakgosciu = None
                                    wywozyudane = 0
                                    atakczyprzeciwnik = 0
            if wywozyudane == 1 and atak == 0:
                wytwornie[primary_id3 + ' kasa'] += kasa
                amounts[primary_id] += kasa
                wytwornie[primary_id3 + ' zasoby'] = 0
                wytwornie[primary_id3 + ' wywoz'] = 0
                _save()
                await asyncio.sleep(1)
                _upload()
                embed = discord.Embed(title="Wywozy u " + str(ctx.message.author.name) + ' udane! 🚚', description=' Zarobiono: '+ str(kasa) + ' Social Credit!', colour=discord.Color.green())
                embed.set_thumbnail(url = 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/OOjs_UI_icon_lock.svg/768px-OOjs_UI_icon_lock.svg.png')
                message4 = await ctx.send(embed=embed)
                kasa = 0
                atak = 0
                wywozi = 0
                atakgosciu = None
                wywozyudane = 0
                atakczyprzeciwnik = 0



@client.command(pass_context=True)
async def atak(ctx):
    global wywozi
    global atakczyprzeciwnik
    global atak
    global wytwornie
    global atakgosciu
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if str(ctx.message.author.id) + ' wytwornia zasoby' in wytwornie:
        if wywozi == 1 and atakczyprzeciwnik == 0:
            atakgosciu = ctx.message.author
            atakczyprzeciwnik = 1
            atak = 1
            await ctx.message.delete()





@client.command(pass_context=True)
async def dajquest(ctx):
    global questchoose
    id = str(ctx.message.author.id)
    id2 = id
    name = str(ctx.message.author.name)
    curq = str(random.choice(questchoose))
    if id2 not in quests or quests[id2] == '':
        curq = str(random.choice(questchoose))
        quests[id] = str(curq)
        if curq == 'Wykop 3 razy cos w kopalni':
            quests[str(ctx.message.author.name)] = 3
        if curq == 'Zagraj i wygraj na ruletce':
            quests[str(ctx.message.author.name)] = 1
        if curq == 'Kup pozdrowienia od Johna Xiny':
            quests[str(ctx.message.author.name)] = 1
        if curq == 'Napisz h na ✍-h':
            quests[str(ctx.message.author.name)] = 1


        await ctx.send("Oto twój quest: " + str(curq))
        _save()
        await asyncio.sleep(1)
        _upload()


    else:
        await ctx.send("Już masz questa wtf")


@client.command(pass_context=True)
@has_permissions(kick_members=True, ban_members=True)
async def przymusowarejestracja(ctx, other: discord.Member):
    id = str(other.id)
    id2 = id + ' kasa'
    name = str(ctx.message.author.name)
    if id2 not in amounts:
        amounts[id + ' kasa'] = 100
        amounts[id + ' awanturniczosc'] = 100
        await ctx.send(str(other.display_name) + " Od teraz jest zarejestrowany!")
        _save()
        await asyncio.sleep(1)
        _upload()

    else:
        await ctx.send("On już ma konto")

@client.command(pass_context=True)
async def zaplac(ctx, amount: int, other: discord.Member):
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    other_id2 = str(other.id)
    other_id = other_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif other_id not in amounts:
        await ctx.send("Gościu nie ma konta")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        amounts[other_id] += amount
        await ctx.send("Transakcja przebiegła pomyślnie!")
    _save()
    await asyncio.sleep(1)
    _upload()


@client.command(pass_context=True)
@has_permissions(kick_members=True, ban_members=True)
async def grzywna(ctx, amount: int, other: discord.Member):
    other_id2 = str(ctx.message.author.id)
    other_id = other_id2 + ' kasa'
    primary_id2 = str(other.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Gościu nie ma konta :( Musi się zarejestrować sc!zarejestruj albo sc!przymusowarejestracja")
    elif other_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    elif primary_id == '264079253757231104 kasa':
        await ctx.send("No co ty prezydenta??????")
    else:
        global creditplusimages

        amounts[primary_id] -= amount
        amounts[other_id] += amount
        embed = discord.Embed(title="Grzywna!!!", description=str(other.display_name) + ' Został poddany karze grzywny w wysokości ' + str(amount) + ' social credit!', colour=discord.Color.red())
        embed.set_thumbnail(url = random.choice(creditplusimages))
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()

@client.command(pass_context=True)
@has_permissions(kick_members=True, ban_members=True)
async def dajsocial(ctx, amount: int, other: discord.Member):
    if ctx.message.author.id == 264079253757231104 or ctx.message.author.id == 212988300137463809 or ctx.message.author.id == 347074207361794068:
        other_id2 = str(ctx.message.author.id)
        other_id = other_id2 + ' kasa'
        primary_id2 = str(other.id)
        primary_id = primary_id2 + ' kasa'
        if primary_id not in amounts:
            await ctx.send("Gościu nie ma konta :( Musi się zarejestrować sc!zarejestruj albo sc!przymusowarejestracja")
        elif other_id not in amounts:
            await ctx.send("Nie masz konta! sc!zarejestruj")
        else:
            global creditsocialimages
            amounts[primary_id] += amount
            embed = discord.Embed(title="+ Social Credit 👍!!!", description=str(other.display_name) + ' Otrzymał ' + str(amount) + ' social credit!', colour=discord.Color.green())
            embed.set_thumbnail(url = random.choice(creditsocialimages))
            message4 = await ctx.send(embed=embed)

            await ctx.message.delete()
        _save()
        await asyncio.sleep(1)
        _upload()
    else:
        amount = 5
        amounts[str(ctx.message.author.id) + ' kasa'] -= amount
        embed = discord.Embed(title="Grzywna!!!", description=str(ctx.message.author.name) + ' Został poddany karze grzywny w wysokości ' + str(amount) + ' social credit za próbe dania se za free kredytów!', colour=discord.Color.red())
        embed.set_thumbnail(url = random.choice(creditplusimages))
        message4 = await ctx.send(embed=embed)
        _save()
        await asyncio.sleep(1)
        _upload()




@client.command(pass_context=True)
async def saldotego(ctx, other: discord.Member):
    id2 = str(other.id)
    id = id2 + ' kasa'
    if id in amounts:
        await ctx.send(str(other.display_name) + " ma {} social credit w banku".format(amounts[id]))
        await ctx.message.delete()
    else:
        await ctx.send("Nie ma konta. zarejestruj go sc!przymusowarejestracja")

@client.command(pass_context=True)
async def kupvip(ctx):
    amount = 760
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        viprank = discord.utils.find(lambda r: r.name == '💎VIP', ctx.guild.roles)
        await ctx.message.author.add_roles(viprank)
        embed = discord.Embed(title="💎Zakupiono VIP💎", description=str(ctx.message.author.display_name) + ' Otrzymał range VIP za ' + str(amount) + ' social credit!', colour=discord.Color.blue())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()


@client.command(pass_context=True)
async def kupprzepustke(ctx):
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    amount = gulaggrzywna[primary_id]
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        if amount <= 0:
            amount = 100
        elif amounts[primary_id] < amount:
            await ctx.send("Nie można przetworzyć transakcji")
        amounts[primary_id] -= amount
        gulaggrzywna[primary_id] = 0
        member = ctx.message.author
        var = discord.utils.get(ctx.message.guild.roles, name = "PszczelarzHell")
        await member.remove_roles(var)
        embed = discord.Embed(title="Wykupiono Przepustke", description=str(ctx.message.author.display_name) + ' Otrzymał możliwość wyjścia z gułagu za ' + str(amount) + ' social credit!', colour=discord.Color.green())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()





@client.command(pass_context=True)
async def kuprangescp(ctx):
    amount = 1
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        viprank = discord.utils.find(lambda r: r.name == 'SCP:SL 🎮', ctx.guild.roles)
        await ctx.message.author.add_roles(viprank)
        embed = discord.Embed(title="Zakupiono SCP:SL 🎮", description=str(ctx.message.author.display_name) + ' Otrzymał range SCP:SL  za ' + str(amount) + ' social credit! Od teraz będziesz powiadamiany gdy któś oznaczy tą grę!', colour=discord.Color.blue())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()

@client.command(pass_context=True)
async def kuprangerdo(ctx):
    amount = 1
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        viprank = discord.utils.find(lambda r: r.name == 'Red Dead Online 🎮', ctx.guild.roles)
        await ctx.message.author.add_roles(viprank)
        embed = discord.Embed(title="Zakupiono Red Dead Online 🎮", description=str(ctx.message.author.display_name) + ' Otrzymał range Red Dead Online za ' + str(amount) + ' social credit! Od teraz będziesz powiadamiany gdy któś oznaczy tą grę!', colour=discord.Color.blue())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()


@client.command(pass_context=True)
async def kuprangegtav(ctx):
    amount = 1
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        viprank = discord.utils.find(lambda r: r.name == 'GTA V🎮', ctx.guild.roles)
        await ctx.message.author.add_roles(viprank)
        embed = discord.Embed(title="Zakupiono GTA V🎮", description=str(ctx.message.author.display_name) + ' Otrzymał range GTA V  za ' + str(amount) + ' social credit! Od teraz będziesz powiadamiany gdy któś oznaczy tą grę!', colour=discord.Color.blue())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()

@client.command(pass_context=True)
async def kuprangefallout76(ctx):
    amount = 1
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        viprank = discord.utils.find(lambda r: r.name == 'Fallout 76🎮', ctx.guild.roles)
        await ctx.message.author.add_roles(viprank)
        embed = discord.Embed(title="Zakupiono Fallout 76🎮", description=str(ctx.message.author.display_name) + ' Otrzymał range Fallout 76 za ' + str(amount) + ' social credit! Od teraz będziesz powiadamiany gdy któś oznaczy tą grę!', colour=discord.Color.blue())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()

@client.command(pass_context=True)
async def kuprangeoverwatch(ctx):
    amount = 1
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        viprank = discord.utils.find(lambda r: r.name == 'Overwatch 🎮', ctx.guild.roles)
        await ctx.message.author.add_roles(viprank)
        embed = discord.Embed(title="Zakupiono Overwatch 🎮", description=str(ctx.message.author.display_name) + ' Otrzymał range Overwatch za ' + str(amount) + ' social credit! Od teraz będziesz powiadamiany gdy któś oznaczy tą grę!', colour=discord.Color.blue())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()

@client.command(pass_context=True)
async def kuprangecsgo(ctx):
    amount = 1
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        viprank = discord.utils.find(lambda r: r.name == 'Counter Train: Deleted Offensive 🎮', ctx.guild.roles)
        await ctx.message.author.add_roles(viprank)
        embed = discord.Embed(title="Zakupiono Counter Strike🎮", description=str(ctx.message.author.display_name) + ' Otrzymał range Counter Strike za ' + str(amount) + ' social credit! Od teraz będziesz powiadamiany gdy któś oznaczy tą grę!', colour=discord.Color.blue())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()

@client.command(pass_context=True)
async def kuprangeligaliga(ctx):
    amount = 1
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        viprank = discord.utils.find(lambda r: r.name == 'Liga Liga Liga Liga Liga (top wolny) 🎮', ctx.guild.roles)
        await ctx.message.author.add_roles(viprank)
        embed = discord.Embed(title="Zakupiono Liga Liga Liga Liga Liga (top wolny) 🎮", description=str(ctx.message.author.display_name) + ' Otrzymał range Liga Liga Liga Liga Liga (top wolny) za ' + str(amount) + ' social credit! Od teraz będziesz powiadamiany gdy któś oznaczy tą grę!', colour=discord.Color.blue())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()


@client.command(pass_context=True)
async def kuprangekumpel(ctx):
    amount = 50
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        viprank = discord.utils.find(lambda r: r.name == '😊Kumpel', ctx.guild.roles)
        await ctx.message.author.add_roles(viprank)
        embed = discord.Embed(title="Zakupiono 😊Kumpel", description=str(ctx.message.author.display_name) + ' Otrzymał range Kumpel za ' + str(amount) + ' social credit! Chuja ci to da ale proszę bardzo XD', colour=discord.Color.blue())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()




@client.command(pass_context=True)
async def kuprangedealer(ctx):
    amount = 150
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        viprank = discord.utils.find(lambda r: r.name == 'Dealer🚬', ctx.guild.roles)
        await ctx.message.author.add_roles(viprank)
        embed = discord.Embed(title="Zakupiono Licencje na Dealer🚬", description=str(ctx.message.author.display_name) + ' Otrzymał range Dealer za ' + str(amount) + ' social credit! Od teraz możesz legalnie rozprowadzać towar!!!!', colour=discord.Color.green())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()


@client.command(pass_context=True)
async def kuprangesimp(ctx):
    amount = 150
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        viprank = discord.utils.find(lambda r: r.name == 'SIMP', ctx.guild.roles)
        await ctx.message.author.add_roles(viprank)
        embed = discord.Embed(title="Zakupiono SIMP", description=str(ctx.message.author.display_name) + ' Otrzymał range SIMP za ' + str(amount) + ' social credit!', colour=discord.Color.green())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()


@client.command()
async def kupankieteshort(ctx, *, message=None):
    amount = 50
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    messagefin = message
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        embed = discord.Embed(title="Zakupiono Ankiete", description=str(ctx.message.author.display_name) + ' Kupił 10 minutową ankiete za ' + str(amount) + ' social credit!', colour=discord.Color.green())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
        channel = client.get_channel(902994962877136927)
        rolep = discord.utils.get(ctx.message.author.guild.roles, name="Ankietowicze")
        embed = discord.Embed(title="Ankieta", description= message + '\n' + 'Macie 20 minut na odpowiedź!', colour=discord.Color.purple())
        ping = await channel.send(rolep.mention)
        message = await channel.send(embed=embed)
        await message.add_reaction('👍')
        await message.add_reaction('👎')
        await asyncio.sleep(1)
        cache_message = discord.utils.get(client.cached_messages, id=message.id) #or client.messages depending on your variable
        print(cache_message.reactions)
        await asyncio.sleep(1200)
        reaction1 = get(cache_message.reactions, emoji='👍')
        print(reaction1)
        reaction2 = get(cache_message.reactions, emoji='👎')
        print(reaction2)
        if reaction1.count > reaction2.count:
            embed = discord.Embed(title="Ankieta - Wyniki" , description='W ankiecie '+ str(messagefin) + ' wygrała odpowiedź 👍 z wynikiem '+ str(reaction1.count) + '. Gratuluje! ', colour=discord.Color.purple())
            message2 = await channel.send(embed=embed)
        if reaction2.count > reaction1.count:
            embed = discord.Embed(title="Ankieta - Wyniki" , description='W ankiecie '+ str(messagefin) +' wygrała odpowiedź 👎 z wynikiem '+ str(reaction2.count) + '. Gratuluje! ', colour=discord.Color.purple())
            message3 = await channel.send(embed=embed)
        if reaction2.count == reaction1.count:
            embed = discord.Embed(title="Ankieta - Wyniki", description='W ankiecie '+ str(messagefin) +' wystąpił remis!!!!!!!!🤔', colour=discord.Color.purple())
            message4 = await channel.send(embed=embed)
    _save()
    await asyncio.sleep(1)
    _upload()

@client.command()
async def kupankiete1h(ctx, *, message=None):
    amount = 200
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    messagefin = message
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        embed = discord.Embed(title="Zakupiono Ankiete", description=str(ctx.message.author.display_name) + ' Kupił 1 godzinną ankiete za ' + str(amount) + ' social credit!', colour=discord.Color.green())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
        channel = client.get_channel(902994962877136927)
        allowed_mentions = discord.AllowedMentions(everyone = True)
        await channel.send(content = "@everyone", allowed_mentions = allowed_mentions)
        embed = discord.Embed(title="Ankieta", description= message + '\n' + 'Macie 1 godzine na odpowiedź!', colour=discord.Color.purple())
        message = await channel.send(embed=embed)
        await message.add_reaction('👍')
        await message.add_reaction('👎')
        await asyncio.sleep(1)
        cache_message = discord.utils.get(client.cached_messages, id=message.id) #or client.messages depending on your variable
        print(cache_message.reactions)
        await asyncio.sleep(3600)
        reaction1 = get(cache_message.reactions, emoji='👍')
        print(reaction1)
        reaction2 = get(cache_message.reactions, emoji='👎')
        print(reaction2)
        if reaction1.count > reaction2.count:
            embed = discord.Embed(title="Ankieta - Wyniki" , description='W ankiecie '+ str(messagefin) + ' wygrała odpowiedź 👍 z wynikiem '+ str(reaction1.count) + '. Gratuluje! ', colour=discord.Color.purple())
            message2 = await channel.send(embed=embed)
        if reaction2.count > reaction1.count:
            embed = discord.Embed(title="Ankieta - Wyniki" , description='W ankiecie '+ str(messagefin) +' wygrała odpowiedź 👎 z wynikiem '+ str(reaction2.count) + '. Gratuluje! ', colour=discord.Color.purple())
            message3 = await channel.send(embed=embed)
        if reaction2.count == reaction1.count:
            embed = discord.Embed(title="Ankieta - Wyniki", description='W ankiecie '+ str(messagefin) +' wystąpił remis!!!!!!!!🤔', colour=discord.Color.purple())
            message4 = await channel.send(embed=embed)
    _save()
    await asyncio.sleep(1)
    _upload()


@client.command(pass_context=True)
async def kuprangeankietowicze(ctx):
    amount = 1
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        viprank = discord.utils.find(lambda r: r.name == 'Ankietowicze', ctx.guild.roles)
        await ctx.message.author.add_roles(viprank)
        embed = discord.Embed(title="Zakupiono Ankietowicze", description=str(ctx.message.author.display_name) + ' Otrzymał range Ankietowicze za ' + str(amount) + ' social credit!', colour=discord.Color.green())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()


@client.command(pass_context=True)
async def kuprzwolanieradygaming(ctx):
    amount = 1500
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        rolep = discord.utils.get(ctx.message.author.guild.roles, name="🙏 Święta Trójca GAMINGU")
        ping = await ctx.send(rolep.mention)
        embed = discord.Embed(title="Zwołanie rady!!!!!", description=str(ctx.message.author.display_name) + ' Wykupił zwołanie rady gaming za ' + str(amount) + ' social credit!', colour=discord.Color.green())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()


@client.command(pass_context=True)
async def kop(ctx):
    global nagrodamessage
    amount = randint(1, 15)
    amountaw = 20
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' awanturniczosc'
    primary_id3 = primary_id2 + ' kasa'
    primary_id4 = primary_id2 + ' wytwornia'
    nagroda = randint(1, 5)
    print(str(nagroda))
    if not ctx.message.channel.id == 903724186588037170:
        if not ctx.message.channel.id == 918915483686809612:
            if not ctx.message.channel.id == 932312060715487313:
             return
    if nagroda == 1:
        if primary_id not in amounts:
            await ctx.send("Nie masz konta!")
        elif amounts[primary_id] < amount:
            embed = discord.Embed(title="DOŚĆ!", description=str(ctx.message.author.display_name) + ' Masz dość na dziś. Wróć jutro! Albo napij się piwka :) wpisz sc!kuppiwo aby kupić 60 energi za 20 SC! ', colour=discord.Color.red())
            embed.set_thumbnail(url = 'https://steamuserimages-a.akamaihd.net/ugc/1259267804689234826/7D5687878AE5A05D058C145C6C8614B04A6338CB/')
            message5 = await ctx.send(embed=embed)
            await ctx.message.delete()
        else:
            amount = randint(1, 15)
            amounts[primary_id] -= amountaw
            amounts[primary_id3] += amount
            embed = discord.Embed(title="Wykopano SOCIAL CREDIT👍👍👍👍", description=str(ctx.message.author.display_name) + ' Wykopał ' + str(amount) + ' social creditów!', colour=discord.Color.green())
            embed.set_thumbnail(url = 'https://cdn.pngsumo.com/pickaxe-vector-mining-picture-1147828-pickaxe-transparent-pixelated-mining-pickaxe-png-200_200.png')
            message4 = await ctx.send(embed=embed)
            await ctx.message.delete()
        _save()
        await asyncio.sleep(1)
        _upload()
    if nagroda == 2:
        if primary_id not in amounts:
            await ctx.send("Nie masz konta!")
        elif amounts[primary_id] < amount:
            embed = discord.Embed(title="DOŚĆ!", description=str(ctx.message.author.display_name) + ' Masz dość na dziś. Wróć jutro! Albo napij się piwka :) wpisz sc!kuppiwo aby kupić 60 energi za 20 SC! ', colour=discord.Color.red())
            embed.set_thumbnail(url = 'https://steamuserimages-a.akamaihd.net/ugc/1259267804689234826/7D5687878AE5A05D058C145C6C8614B04A6338CB/')
            message5 = await ctx.send(embed=embed)
            await ctx.message.delete()
        else:
            amounts[primary_id] -= amountaw
            embed = discord.Embed(title="Wykopano", description=str(ctx.message.author.display_name)+' '+  random.choice(nagrodamessage), colour=discord.Color.green())
            embed.set_thumbnail(url = 'https://cdn.pngsumo.com/pickaxe-vector-mining-picture-1147828-pickaxe-transparent-pixelated-mining-pickaxe-png-200_200.png')
            message4 = await ctx.send(embed=embed)
            await ctx.message.delete()
        _save()
        await asyncio.sleep(1)
        _upload()
    if nagroda == 3:
        if primary_id not in amounts:
            await ctx.send("Nie masz konta!")
        elif amounts[primary_id] < amount:
            embed = discord.Embed(title="DOŚĆ!", description=str(ctx.message.author.display_name) + ' Masz dość na dziś. Wróć jutro! Albo napij się piwka :) wpisz sc!kuppiwo aby kupić 60 energi za 20 SC! ', colour=discord.Color.red())
            embed.set_thumbnail(url = 'https://steamuserimages-a.akamaihd.net/ugc/1259267804689234826/7D5687878AE5A05D058C145C6C8614B04A6338CB/')
            message5 = await ctx.send(embed=embed)
            await ctx.message.delete()
        else:
            amount = randint(1, 5)
            amounts[primary_id] -= amountaw
            amounts[primary_id3] += amount
            embed = discord.Embed(title="Wykopano SOCIAL CREDIT👍👍👍👍", description=str(ctx.message.author.display_name) + ' Wykopał ' + str(amount) + ' social creditów!', colour=discord.Color.green())
            embed.set_thumbnail(url = 'https://cdn.pngsumo.com/pickaxe-vector-mining-picture-1147828-pickaxe-transparent-pixelated-mining-pickaxe-png-200_200.png')
            message4 = await ctx.send(embed=embed)
            await ctx.message.delete()
            _save()
            await asyncio.sleep(1)
            _upload()
    if nagroda == 4:
        if primary_id not in amounts:
            await ctx.send("Nie masz konta!")
        elif amounts[primary_id] < amount:
            embed = discord.Embed(title="DOŚĆ!", description=str(ctx.message.author.display_name) + ' Masz dość na dziś. Wróć jutro! Albo napij się piwka :) wpisz sc!kuppiwo aby kupić 60 energi za 20 SC! ', colour=discord.Color.red())
            embed.set_thumbnail(url = 'https://steamuserimages-a.akamaihd.net/ugc/1259267804689234826/7D5687878AE5A05D058C145C6C8614B04A6338CB/')
            message5 = await ctx.send(embed=embed)
            await ctx.message.delete()
        else:
            amount = randint(1, 100)
            amounts[primary_id] -= amountaw
            amounts[primary_id3] += amount
            embed = discord.Embed(title="Wykopano SOCIAL CREDIT👍👍👍👍", description=str(ctx.message.author.display_name) + ' Wykopał ' + str(amount) + ' social creditów!', colour=discord.Color.green())
            embed.set_thumbnail(url = 'https://cdn.pngsumo.com/pickaxe-vector-mining-picture-1147828-pickaxe-transparent-pixelated-mining-pickaxe-png-200_200.png')
            message4 = await ctx.send(embed=embed)
            await ctx.message.delete()
            _save()
            await asyncio.sleep(1)
            _upload()
    if nagroda == 5:
        if primary_id not in amounts:
            await ctx.send("Nie masz konta!")
        elif amounts[primary_id] < amount:
            embed = discord.Embed(title="DOŚĆ!", description=str(ctx.message.author.display_name) + ' Masz dość na dziś. Wróć jutro! Albo napij się piwka :) wpisz sc!kuppiwo aby kupić 60 energi za 20 SC! ', colour=discord.Color.red())
            embed.set_thumbnail(url = 'https://steamuserimages-a.akamaihd.net/ugc/1259267804689234826/7D5687878AE5A05D058C145C6C8614B04A6338CB/')
            message5 = await ctx.send(embed=embed)
            await ctx.message.delete()
        elif str(primary_id4 + ' zasoby') not in wytwornie:
            amount = randint(1, 100)
            amounts[primary_id] -= amountaw
            amounts[primary_id3] += amount
            embed = discord.Embed(title="Wykopano SOCIAL CREDIT👍👍👍👍", description=str(ctx.message.author.display_name) + ' Wykopał ' + str(amount) + ' social creditów!', colour=discord.Color.green())
            embed.set_thumbnail(url = 'https://cdn.pngsumo.com/pickaxe-vector-mining-picture-1147828-pickaxe-transparent-pixelated-mining-pickaxe-png-200_200.png')
            message4 = await ctx.send(embed=embed)
            await ctx.message.delete()
            _save()
            await asyncio.sleep(1)
            _upload()
        else:
            amount = randint(1, 40)
            amounts[primary_id] -= amountaw
            wytwornie[str(primary_id4 + ' zasoby')] += amount
            embed = discord.Embed(title="Wykopano Zasoby👍👍👍👍", description=str(ctx.message.author.display_name) + ' Wykopał ' + str(amount) + ' zasobów!', colour=discord.Color.green())
            embed.set_thumbnail(url = 'https://cdn.pngsumo.com/pickaxe-vector-mining-picture-1147828-pickaxe-transparent-pixelated-mining-pickaxe-png-200_200.png')
            message4 = await ctx.send(embed=embed)
            await ctx.message.delete()
            _save()
            await asyncio.sleep(1)
            _upload()

@client.command(pass_context=True)
async def kuppozdrowienia(ctx, member: discord.Member):
    global amounts
    global quests
    amount = 15
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        embed = discord.Embed(title="Zakupiono Pozdrowienia od Johna Xiny!!!", description=str(ctx.message.author.display_name) + ' kupił podrowienia dla ' +str(member.display_name)+' za ' + str(amount) + ' social credit!', colour=discord.Color.green())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
        channel = member.voice.channel
        voice = get(client.voice_clients, guild=ctx.guild)
        if voice and voice.is_connected():

            await voice.move_to(channel)
            voice.play(discord.FFmpegPCMAudio( source="xina.mp3"))
            if quests[str(ctx.message.author.id)] == 'Kup pozdrowienia od Johna Xiny' and quests[str(ctx.message.author.name)] == 1:
                print('ma skonczony quest')
                quests[str(ctx.message.author.name)] = 0
                quests[str(ctx.message.author.id)] = ''
                amount = 20
                if str(ctx.message.author.id) + ' kasa' in amounts:
                    print('jest')
                    amounts[str(ctx.message.author.id) + ' kasa'] += amount
                    embed = discord.Embed(title="+ Social Credit 👍!!!", description=str(ctx.message.author.name) + ' Otrzymał ' + str(amount) + ' social credit za wykonanie questa!', colour=discord.Color.green())
                    embed.set_thumbnail(url = random.choice(creditsocialimages))
                    message4 = await ctx.send(embed=embed)
                    _save()
                    await asyncio.sleep(1)
                    _upload()
            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            await voice.disconnect()
            print('wychodze!!!')
        else:

            voice = await channel.connect()
            voice.play(discord.FFmpegPCMAudio( source="xina.mp3"))
            if quests[str(ctx.message.author.id)] == 'Kup pozdrowienia od Johna Xiny' and quests[str(ctx.message.author.name)] == 1:
                print('ma skonczony quest')
                quests[str(ctx.message.author.name)] = 0
                quests[str(ctx.message.author.id)] = ''
                amount = 20
                if str(ctx.message.author.id) + ' kasa' in amounts:
                    print('jest')
                    amounts[str(ctx.message.author.id) + ' kasa'] += amount
                    embed = discord.Embed(title="+ Social Credit 👍!!!", description=str(ctx.message.author.name) + ' Otrzymał ' + str(amount) + ' social credit za wykonanie questa!', colour=discord.Color.green())
                    embed.set_thumbnail(url = random.choice(creditsocialimages))
                    message4 = await ctx.send(embed=embed)
                    _save()
                    await asyncio.sleep(1)
                    _upload()

            while voice.is_playing():
                print('gra')
                await asyncio.sleep(2)
            await voice.disconnect()
            print('wychodze!!!')

    _save()
    await asyncio.sleep(1)
    _upload()


@client.command(pass_context=True)
async def kuppiwo(ctx):
    global nagrodamessage
    amountaw = 60
    amount = 20
    primary_id2 = str(ctx.message.author.id)
    awan = primary_id2 + ' awanturniczosc'
    kasap = primary_id2 + ' kasa'
    if awan not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[awan] >= 100:
        embed = discord.Embed(title="DOŚĆ!", description=str(ctx.message.author.display_name) + ' Masz dość na dziś. Wróć jutro pijaku!:)', colour=discord.Color.red())
        embed.set_thumbnail(url = 'https://steamuserimages-a.akamaihd.net/ugc/1259267804689234826/7D5687878AE5A05D058C145C6C8614B04A6338CB/')
        message5 = await ctx.send(embed=embed)
        await ctx.message.delete()
    elif amounts[kasap] < amount:
        embed = discord.Embed(title="Nie masz kasy", description=str(ctx.message.author.display_name) + ' We wróć z creditami a nie!', colour=discord.Color.red())
        embed.set_thumbnail(url = 'https://steamuserimages-a.akamaihd.net/ugc/1259267804689234826/7D5687878AE5A05D058C145C6C8614B04A6338CB/')
        message5 = await ctx.send(embed=embed)
        await ctx.message.delete()
    else:
        amounts[awan] += amountaw
        amounts[kasap] -= amount
        embed = discord.Embed(title="Wypito piwo🍺", description=str(ctx.message.author.display_name) + ' Wypił/a piwo przywracając sobie ' + str(amountaw) + ' energii!', colour=discord.Color.green())
        embed.set_thumbnail(url = 'https://steamuserimages-a.akamaihd.net/ugc/1259267804689234826/7D5687878AE5A05D058C145C6C8614B04A6338CB/')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()

@client.command(pass_context=True)
async def przywrocenergie(ctx):
    if ctx.message.author.id == 264079253757231104:
        curguild = client.get_guild(637696690853511184)
        curguild2 = client.get_guild(706179463288979519)
        await ctx.message.add_reaction('✅')
        for guild in client.guilds:
            for member in curguild.members:
                if str(member.id) + ' awanturniczosc' not in amounts:
                    print(str(member.display_name) + " Nie ma konta!")
                elif member.bot == True:
                    print('BOT')
                else:
                    if amounts[str(member.id) + ' awanturniczosc'] < 100:
                        amounts[str(member.id) + ' awanturniczosc'] = 100
                        print(str(member.display_name) + " dano energie")
                    _save()
                    await asyncio.sleep(1)
                    _upload()
            for member in curguild2.members:
                if str(member.id) + ' awanturniczosc' not in amounts:
                    print(str(member.display_name) + " Nie ma konta!")
                elif member.bot == True:
                    print('BOT')
                else:
                    if amounts[str(member.id) + ' awanturniczosc'] < 100:
                        amounts[str(member.id) + ' awanturniczosc'] = 100
                        print(str(member.display_name) + " dano energie")
                    _save()
                    await asyncio.sleep(1)
                    _upload()




@client.command(pass_context=True)
async def kanalniskielo(ctx):
    member = ctx.message.author
    amount = 10
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    messagetext = ctx.message.clean_content
    finaltext = messagetext.replace('sc!kanalniskielo','')
    print(finaltext)
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        embed = discord.Embed(title="Zakupiono prywatny kanał bez wysokiego LO!", description=str(ctx.message.author.display_name) + ' Wykupił prywatny kanał ' +str(finaltext) + ' za ' + str(amount) + ' social credit!', colour=discord.Color.green())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
        guild = ctx.guild
        mafia_role = get(guild.roles, name="❌ Wysokie LO")
        user_role = get(guild.roles, name="🎮Gamer")
        user2_role = get(guild.roles, name="✔️Niske LO")
        guild = ctx.message.guild
        cat = discord.utils.get(ctx.guild.categories, name="🔊 GADANIE")
        overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        mafia_role: discord.PermissionOverwrite(read_messages=False),
        user_role: discord.PermissionOverwrite(read_messages=False),
        user2_role: discord.PermissionOverwrite(read_messages=True)

        }
        channel2 = await guild.create_voice_channel("🎮 " + str(finaltext) + " (low LO)", category=cat, overwrites=overwrites)
        channel = channel2

    _save()
    await asyncio.sleep(1)
    _upload()


@client.command(pass_context=True)
async def kupprivkanal(ctx):
    amount = 10
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    messagetext = ctx.message.clean_content
    finaltext = messagetext.replace('sc!kupprivkanal','')
    print(finaltext)
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        embed = discord.Embed(title="Zakupiono prywatny kanał!", description=str(ctx.message.author.display_name) + ' Wykupił prywatny kanał ' +str(finaltext) + ' za ' + str(amount) + ' social credit!', colour=discord.Color.green())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
        guild = ctx.message.guild
        cat = discord.utils.get(ctx.guild.categories, name="🔊 GADANIE")
        channel = await guild.create_voice_channel(str(finaltext), category=cat)
    _save()
    await asyncio.sleep(1)
    _upload()




@client.command()
async def kupeveryone(ctx, *, message=None):
    amount = 1500
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        embed = discord.Embed(title="Zakupiono Everyone", description=str(ctx.message.author.display_name) + ' ping everyone za ' + str(amount) + ' social credit!', colour=discord.Color.green())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()

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
        allowed_mentions = discord.AllowedMentions(everyone = True)
        await channel.send(content = "@everyone", allowed_mentions = allowed_mentions)
        _save()
        await asyncio.sleep(1)
        _upload()


def _save():
    with open('amounts.json', 'w+') as f:
        json.dump(amounts, f)
    with open('quests.json', 'w+') as d:
        json.dump(quests, d)
    with open('wytwornie.json', 'w+') as g:
        json.dump(wytwornie, g)
    with open('nfts.json', 'w+') as k:
        json.dump(nfts, k)
    with open('nftowners.json', 'w+') as m:
        json.dump(nftowners, m)
    with open('grzywna.json', 'w+') as h:
        json.dump(gulaggrzywna, h)




def _upload():
    HOSTNAME = "ftpupload.net"
    USERNAME = "unaux_30223757"
    PASSWORD = "il6c9pl"
    # Connect FTP Server
    ftp_server = ftplib.FTP(HOSTNAME, USERNAME, PASSWORD)
    # force UTF-8 encoding
    ftp_server.encoding = "utf-8"
    # Get list of files
    ftp_server.cwd('htdocs')
    ftp_server.dir()
    # Enter File Name with Extension
    filename = "amounts.json"
    filename2 = "quests.json"
    filename3 = "wytwornie.json"
    filename4 = "grzywna.json"
    filename5 = "nfts.json"
    filename6 = "nftowners.json"
    # Read file in binary mode
    with open(filename, "rb") as file:
        # Command for Uploading the file "STOR filename"
        ftp_server.storbinary(f"STOR {filename}", file)
        print('wysyłano' + str({filename}))
    with open(filename3, "rb") as file3:
        # Command for Uploading the file "STOR filename"
        ftp_server.storbinary(f"STOR {filename3}", file3)
        print('wysyłano' + str({filename3}))
    with open(filename4, "rb") as file4:
        # Command for Uploading the file "STOR filename"
        ftp_server.storbinary(f"STOR {filename4}", file4)
        print('wysyłano' + str({filename4}))
    with open(filename5, "rb") as file5:
        # Command for Uploading the file "STOR filename"
        ftp_server.storbinary(f"STOR {filename5}", file5)
        print('wysyłano' + str({filename5}))
    with open(filename6, "rb") as file6:
        # Command for Uploading the file "STOR filename"
        ftp_server.storbinary(f"STOR {filename6}", file6)
        print('wysyłano' + str({filename6}))
    with open(filename2, "rb") as file2:
        # Command for Uploading the file "STOR filename"
        ftp_server.storbinary(f"STOR {filename2}", file2)
        print('wysyłano' + str({filename2}))
        ftp_server.quit()
        print("zerwano połączenie ręcznie")


@client.command(pass_context=True)
async def ruletka(ctx, amount: int, zaklad: str):
    global gracze
    global graczewygrani
    global start
    global start2
    global czyjuzuruchomiono
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        global gracze
        if not str(ctx.author.id) in gracze and start2 == 0 and not amount == 0:
            gracze[str(ctx.author.id)] = amount
            gracze[str(ctx.author.name)] = zaklad
            print(gracze)
            if len(gracze) < 4 and start == 0 and start2 == 0:
                amounts[primary_id] -= amount
                embed = discord.Embed(title="Dołączono do gry ✔️", description=str(ctx.message.author.display_name) + ' Postawił  '+ str(amount)  + ' social credit' + ' na ' + str(zaklad) + '! Oczekiwanie na chociaż jeszcze 1 osobę!', colour=discord.Color.green())
                embed.set_thumbnail(url = 'https://steamuserimages-a.akamaihd.net/ugc/1259267804689230657/DBB91CA04323894EEBD062A677DC84D009377F87/')
                message4 = await ctx.send(embed=embed)
                await ctx.message.delete()
                print('za mało osób')
                _save()
                await asyncio.sleep(1)
                _upload()
            if len(gracze) == 4 and start == 0:
                amounts[primary_id] -= amount
                embed = discord.Embed(title="Dołączono do gry ✔️", description=str(ctx.message.author.display_name) + ' postawił  '+ str(amount)  + ' social credit' + ' na ' + str(zaklad), colour=discord.Color.green())
                embed.set_thumbnail(url = 'https://steamuserimages-a.akamaihd.net/ugc/1259267804689230657/DBB91CA04323894EEBD062A677DC84D009377F87/')
                message4 = await ctx.send(embed=embed)
                await ctx.message.delete()
                print(gracze)
                print('zaczynamy')
                start = 1
                _save()
                await asyncio.sleep(1)
                _upload()
            if len(gracze) >= 6 and start2 == 0:
                amounts[primary_id] -= amount
                embed = discord.Embed(title="Dołączono do gry ✔️", description=str(ctx.message.author.display_name) + ' Postawił  '+ str(amount)  + ' social credit' + ' na ' + str(zaklad), colour=discord.Color.green())
                embed.set_thumbnail(url = 'https://steamuserimages-a.akamaihd.net/ugc/1259267804689230657/DBB91CA04323894EEBD062A677DC84D009377F87/')
                message4 = await ctx.send(embed=embed)
                await ctx.message.delete()
                print('dużo osób')
                czyjuzuruchomiono = 1
                _save()
                await asyncio.sleep(1)
                _upload()
            if start == 1 and czyjuzuruchomiono == 0:
                embed = discord.Embed(title="Gra rozpoczyna się za 30 sekund! ⏱️", description=' dołączajcie póki możecie!', colour=discord.Color.dark_orange())
                embed.set_thumbnail(url = 'https://steamuserimages-a.akamaihd.net/ugc/1259267804689230657/DBB91CA04323894EEBD062A677DC84D009377F87/')
                message76 = await ctx.send(embed=embed)
                await asyncio.sleep(30)
                start2 = 1
                wynik = randint(1, 12)
                print(wynik)
                message8 = await ctx.send(file=discord.File('ruletka//ruletkaspin.gif'))
                await asyncio.sleep(3)
                cache_message = discord.utils.get(client.cached_messages, id=message8.id) #or client.messages depending on your variable
                if wynik == 1:
                    cache_message = discord.utils.get(client.cached_messages, id=message8.id) #or client.messages depending on your variable
                    await cache_message.delete()
                    message9 = await ctx.send(file=discord.File('ruletka//frame_1_delay-0.1s.gif'))
                    kolor = "red"
                if wynik == 2:
                    await asyncio.sleep(0.001)
                    cache_message = discord.utils.get(client.cached_messages, id=message8.id) #or client.messages depending on your variable
                    await cache_message.delete()
                    message9 = await ctx.send(file=discord.File('ruletka//frame_2_delay-0.1s.gif'))
                    kolor = "red"
                if wynik == 3:
                    await asyncio.sleep(0.1)
                    cache_message = discord.utils.get(client.cached_messages, id=message8.id) #or client.messages depending on your variable
                    await cache_message.delete()
                    message9 = await ctx.send(file=discord.File('ruletka//frame_3_delay-0.1s.gif'))
                    kolor = "black"
                if wynik == 4:
                    await asyncio.sleep(0.2)
                    cache_message = discord.utils.get(client.cached_messages, id=message8.id) #or client.messages depending on your variable
                    await cache_message.delete()
                    message9 = await ctx.send(file=discord.File('ruletka//frame_4_delay-0.1s.gif'))
                    kolor = "black"
                if wynik == 5:
                    await asyncio.sleep(0.3)
                    cache_message = discord.utils.get(client.cached_messages, id=message8.id) #or client.messages depending on your variable
                    await cache_message.delete()
                    message9 = await ctx.send(file=discord.File('ruletka//frame_5_delay-0.1s.gif'))
                    kolor = "black"
                if wynik == 6:
                    await asyncio.sleep(0.4)
                    cache_message = discord.utils.get(client.cached_messages, id=message8.id) #or client.messages depending on your variable
                    await cache_message.delete()
                    message9 = await ctx.send(file=discord.File('ruletka//frame_6_delay-0.1s.gif'))
                    kolor = "black"
                if wynik == 7:
                    await asyncio.sleep(0.5)
                    cache_message = discord.utils.get(client.cached_messages, id=message8.id) #or client.messages depending on your variable
                    await cache_message.delete()
                    message9 = await ctx.send(file=discord.File('ruletka//frame_7_delay-0.1s.gif'))
                    kolor = "red"
                if wynik == 8:
                    await asyncio.sleep(0.6)
                    cache_message = discord.utils.get(client.cached_messages, id=message8.id) #or client.messages depending on your variable
                    await cache_message.delete()
                    message9 = await ctx.send(file=discord.File('ruletka//frame_8_delay-0.1s.gif'))
                    kolor = "red"
                if wynik == 9:
                    await asyncio.sleep(0.7)
                    cache_message = discord.utils.get(client.cached_messages, id=message8.id) #or client.messages depending on your variable
                    await cache_message.delete()
                    message9 = await ctx.send(file=discord.File('ruletka//frame_9_delay-0.1s.gif'))
                    kolor = "red"
                if wynik == 10:
                    await asyncio.sleep(0.8)
                    cache_message = discord.utils.get(client.cached_messages, id=message8.id) #or client.messages depending on your variable
                    await cache_message.delete()
                    message9 = await ctx.send(file=discord.File('ruletka//frame_10_delay-0.1s.gif'))
                    kolor = "red"
                if wynik == 11:
                    await asyncio.sleep(0.8)
                    cache_message = discord.utils.get(client.cached_messages, id=message8.id) #or client.messages depending on your variable
                    await cache_message.delete()
                    message9 = await ctx.send(file=discord.File('ruletka//frame_11_delay-0.1s.gif'))
                    kolor = "black"
                if wynik == 12:
                    await asyncio.sleep(0.8)
                    cache_message = discord.utils.get(client.cached_messages, id=message8.id) #or client.messages depending on your variable
                    await cache_message.delete()
                    message9 = await ctx.send(file=discord.File('ruletka//frame_12_delay-0.1s.gif'))
                    kolor = "black"
                await asyncio.sleep(1)
                for guild in client.guilds:
                    for member in ctx.guild.members:
                        if str(member.name) in gracze:
                            print(member.name)
                            if gracze[str(member.name)] == kolor:
                                print("wygrał!")
                                if str(member.id) in gracze:
                                    winr = gracze[str(member.id)]
                                    idwygranego2 = str(member.id)
                                    idwygranego = idwygranego2 + ' kasa'
                                    print(str(winr))
                                    winrfinal = winr * 2
                                    print(str(winrfinal))
                                    print(str(amounts[idwygranego]))
                                    amounts[idwygranego] += winrfinal
                                    print(str(amounts[idwygranego]))
                                    if quests[str(member.id)] == 'Zagraj i wygraj na ruletce' and quests[str(member.name)] == 1:
                                        print('ma skonczony quest')
                                        quests[str(member.name)] = 0
                                        quests[str(member.id)] = ''
                                        amount = 20
                                        if str(member.id) + ' kasa' in amounts:
                                            print('jest')
                                            amounts[str(member.id) + ' kasa'] += amount
                                            embed = discord.Embed(title="+ Social Credit 👍!!!", description=str(member.display_name) + ' Otrzymał ' + str(amount) + ' social credit za wykonanie questa!', colour=discord.Color.green())
                                            embed.set_thumbnail(url = random.choice(creditsocialimages))
                                            message983 = await ctx.send(embed=embed)
                                            _save()
                                    gracze.pop(str(member.id),None)
                                    gracze.pop(str(member.name),None)
                                    print(gracze)
                                    _save()
                                    await asyncio.sleep(1)
                                    _upload()
                                    graczewygrani.append(member.display_name)
                                    print(graczewygrani)
                graczewygrani.sort()
                wfinaltext = str(graczewygrani).replace('[','')
                wfinaltext2 = str(wfinaltext).replace(']','')
                wfinaltext3 = str(wfinaltext2).replace("'",'')
                wfinaltext4 = str(wfinaltext3).replace(",",', \n')
                print(wfinaltext4)
                embed = discord.Embed(title="Wygrali 🏆", description= wfinaltext4, colour=discord.Color.gold())
                embed.set_thumbnail(url = 'https://steamuserimages-a.akamaihd.net/ugc/1259267804689230657/DBB91CA04323894EEBD062A677DC84D009377F87/')
                message4 = await ctx.send(embed=embed)
                gracze = {}
                graczewygrani = []
                start = 0
                start2 = 0
                czyjuzuruchomiono = 0
        else:
            embed = discord.Embed(title="Już jesteś w grze lub użyłeś niedozwolonej liczby ❌", description=str(ctx.message.author.display_name) +  ' Co ty chcesz wariacie! Tak się nie robi', colour=discord.Color.dark_red())
            embed.set_thumbnail(url = 'https://steamuserimages-a.akamaihd.net/ugc/1259267804689230657/DBB91CA04323894EEBD062A677DC84D009377F87/')
            message4 = await ctx.send(embed=embed)
            await ctx.message.delete()


def _ruletka():
    print("tak")


@client.command()
async def serverupdate(ctx):
    _save()
    await asyncio.sleep(1)
    _upload()
    await ctx.send('Wysłano info na serwer!')


@client.command()
async def ping(ctx):
    await ctx.send('Chwała dyktatorowi!')

@tasks.loop(seconds=3)
async def change_status():
    await client.change_presence(activity=discord.Game(next(status)))

@tasks.loop(seconds=30)
async def change_kopanie():
    if "02:00" in str(datetime.datetime.now().time()):
        print("nadszedł czas")
        curguild = client.get_guild(637696690853511184)
        curguild2 = client.get_guild(706179463288979519)
        for member in curguild.members:
            if str(member.id) + ' awanturniczosc' in amounts:
                if amounts[str(member.id) + ' awanturniczosc'] < 100:
                    amounts[str(member.id) + ' awanturniczosc'] = 100
                    print(str(member.display_name) + " dano energie")
                    _save()
                    await asyncio.sleep(1)
                    _upload()
        for member in curguild2.members:
            if str(member.id) + ' awanturniczosc' in amounts:
                if amounts[str(member.id) + ' awanturniczosc'] < 100:
                    amounts[str(member.id) + ' awanturniczosc'] = 100
                    print(str(member.display_name) + " dano energie")
                    _save()
                    await asyncio.sleep(1)
                    _upload()





@tasks.loop(seconds=35)
async def change_wyplata():
    global czydalowyplate
    czas = str(datetime.datetime.now().time())
    curguild = client.get_guild(637696690853511184)
    ranga = discord.utils.find(lambda r: r.name == '💸 Hrabia', curguild.roles)
    channel = client.get_channel(1100193218907349112)
    if "15:00" in czas and czydalowyplate == 0:
        print("nadszedł czas")
        czydalowyplate = 1
        for member in curguild.members:
            if ranga in member.roles:
                amount = 50
                amounts[str(member.id) + ' kasa'] += amount
                print(str(member.display_name) + " dano mu kase za oplacanie serwera")
                _save()
                await asyncio.sleep(1)
                _upload()
                global creditsocialimages
                embed = discord.Embed(title="+ Dzienny Social Credit 👍!!!", description=str(member.display_name) + ' Otrzymał ' + str(amount) + ' social credit za opłacanie serwera💸💸💸! Jutro kolejne :)', colour=discord.Color.magenta())
                embed.set_thumbnail(url = random.choice(creditsocialimages))
                message4 = await channel.send(embed=embed)
            else:
                print(str(member.display_name) + ' nie ma hrabii')
    if "15:01" in czas and czydalowyplate == 1:
        czydalowyplate = 0



@tasks.loop(hours=1)
async def change_pobieranie():
     if os.stat('amounts.json').st_size > 0:
       print("All good")
     else:
       global amounts
       global base
       try:
           # Connect FTP Server
           ftp_server = ftplib.FTP(HOSTNAME, USERNAME, PASSWORD)

           # force UTF-8 encoding
           ftp_server.encoding = "utf-8"
           # Get list of files
           ftp_server.cwd('htdocs')
           ftp_server.dir()
           # Enter File Name with Extension
           filename = "amounts.json"
           # Write file in binary mode
           with open(filename, "wb") as file:
               # Command for Downloading the file "RETR filename"
               ftp_server.retrbinary(f"RETR {filename}", file.write)
               print('odebrano' + str({filename}))
               base = 0
               await asyncio.sleep(0.1)
               base = 1
           await asyncio.sleep(1)
               # Read file in binary mode
           with open(filename, "rb") as file:
               # Command for Uploading the file "STOR filename"
               ftp_server.storbinary(f"STOR {filename}", file)
               print('wysyłano' + str({filename}))
           # Close the Connection
           await asyncio.sleep(8)
           if base == 1:
               with open('amounts.json') as f:
                   amounts = json.load(f)
                   print("loaded database")
                   ftp_server.quit()
                   print("zerwano połączenie ręcznie")
       except FileNotFoundError:
               print("Could not load amounts.json")
               amounts = {}


@client.event
async def on_member_update(before, after):
    global amounts
    global gryniedozwolone
    global gulaggrzywna
    curguild = client.get_guild(637696690853511184)
    if after.activity and after.activity is not None and str(after.activity.name).lower() in gryniedozwolone:
        if not after.guild.id == 637696690853511184:
            return
        print(str(after.name) + ' gra w niedozwolona gre')
        amount = 1
        if str(after.id) + ' kasa' in amounts:
            print('jest')
            viprank = discord.utils.find(lambda r: r.name == 'PszczelarzHell', after.guild.roles)
            if amounts[str(after.id) + ' kasa'] >= 1:
                channel = client.get_channel(1100193218907349112)
                global creditplusimages
                amount = 0
                amounts[str(after.id) + ' kasa'] = amount
                embed = discord.Embed(title="Grzywna!!!", description=str(after.display_name) + ' Został poddany karze grzywny w wysokości całego majątku social credit za granie w Genshin Impact!', colour=discord.Color.red())
                embed.set_thumbnail(url = random.choice(creditplusimages))
                message4 = await channel.send(embed=embed)
                _save()
                await asyncio.sleep(1)
                _upload()
            if amounts[str(after.id) + ' kasa'] == 0 and not viprank in after.roles:
                gulaggrzywna[str(after.id) + ' kasa'] = 100
                embed = discord.Embed(title="Gułag!!!", description=str(after.display_name) + ' Został wtrącony do gułagu, z możliwością wyjścia za 100 social credit!', colour=discord.Color.red())
                embed.set_thumbnail(url = 'https://superhistoria.pl/_thumb/71/f6/8158f1c635bd1dc262fcfbc9f92d.jpeg')
                message4 = await ctx.send(embed=embed)
                await after.add_roles(viprank)
                _save()
                await asyncio.sleep(1)
                _upload()



@client.event
async def on_message(message):
    global creditplusimages
    global amounts
    global quests
    global creditsocialimages
    global atakgosciu
    global wywozi
    global atakczyprzeciwnik
    global atak
    global wytwornie
    global gulaggrzywna
    global nfts
    global nftowners
    global currentusernfts
    member = message.author
    filetocheck = None
    messageContent1 = message.content.lower()
    messageContent = messageContent1.replace(' ', '')
    channelh = client.get_channel(827293597283647568)
    channelog = client.get_channel(1100193218907349112)
    if str(member.status) == "offline":
        amount = 1
        global amounts
        if str(member.id) + ' kasa' in amounts:
            print('jest')
            if amounts[str(member.id) + ' kasa'] >= 1:
                global creditplusimages
                amount = 1
                amounts[str(member.id) + ' kasa'] -= amount
                embed = discord.Embed(title="Grzywna!!!", description=str(member.display_name) + ' Został poddany karze grzywny w wysokości ' + str(amount) + ' social credit za bycie offline!', colour=discord.Color.red())
                embed.set_thumbnail(url = random.choice(creditplusimages))
                message4 = await message.channel.send(embed=embed)
                _save()
                await asyncio.sleep(1)
                _upload()

    if 'neco' in messageContent:
        amount = 1
        if str(member.id) + ' kasa' in amounts:
            print('jest')
            if amounts[str(member.id) + ' kasa'] >= 1:
                amount = 1
                amounts[str(member.id) + ' kasa'] -= amount
                embed = discord.Embed(title="Grzywna!!!", description=str(member.display_name) + ' Został poddany karze grzywny w wysokości ' + str(amount) + ' social credit za wysyłanie Neco arc!', colour=discord.Color.red())
                embed.set_thumbnail(url = random.choice(creditplusimages))
                message4 = await message.channel.send(embed=embed)
                _save()
                await asyncio.sleep(1)
                _upload()

    if str(member.id) in quests and messageContent == 'sc!kop':
        if quests[str(member.id)] == 'Wykop 3 razy cos w kopalni' and quests[str(member.name)] > 0:
            print('kopalnia quest')
            quests[str(member.name)] -= 1
            _save()
        if quests[str(member.id)] == 'Wykop 3 razy cos w kopalni' and quests[str(member.name)] == 0:
            print('ma skonczony quest')
            quests[str(member.name)] = 0
            quests[str(member.id)] = ''
            amount = 20
            if str(member.id) + ' kasa' in amounts:
                print('jest')
                amounts[str(member.id) + ' kasa'] += amount
                embed = discord.Embed(title="+ Social Credit 👍!!!", description=str(member.display_name) + ' Otrzymał ' + str(amount) + ' social credit za wykonanie questa!', colour=discord.Color.green())
                embed.set_thumbnail(url = random.choice(creditsocialimages))
                message4 = await message.channel.send(embed=embed)
                _save()
                await asyncio.sleep(1)
                _upload()



    if str(member.id) in quests and 'h' in messageContent and message.channel == channelh:
        if quests[str(member.id)] == 'Napisz h na ✍-h' and quests[str(member.name)] == 1:
            print('ma skonczony quest')
            quests[str(member.name)] = 0
            quests[str(member.id)] = ''
            amount = 10
            if str(member.id) + ' kasa' in amounts:
                print('jest')
                amounts[str(member.id) + ' kasa'] += amount
                embed = discord.Embed(title="+ Social Credit 👍!!!", description=str(member.display_name) + ' Otrzymał ' + str(amount) + ' social credit za wykonanie questa!', colour=discord.Color.green())
                embed.set_thumbnail(url = random.choice(creditsocialimages))
                message4 = await channelog.send(embed=embed)
                _save()
                await asyncio.sleep(1)
                _upload()
    if not message.author.id == '903986696658518056' and not 'sc!nftcreate' in messageContent:
        if message.attachments or 'https://' in messageContent:
            print('attachment or link found!')
            if message.attachments:
              attachment = message.attachments[0]
              print(len(message.attachments))
              if len(message.attachments) > 1:
                  attachment2 = message.attachments[1]
                  filetocheck2 = str(attachment2.url)
              filetocheck = str(attachment.url)
              print("atachment")
            if not message.attachments:
              attachment = str(messageContent)
              filetocheck = attachment
              print("link")
            file = filetocheck
            if len(message.attachments) > 1:
                file2 = filetocheck2
            nfttokenfrommessage = ''
            text = file
            silamrityinviewimage = 0
            syf = urlparse(text)
            if len(message.attachments) > 1:
               syf2 = urlparse(file2)
            syf3 = urlparse(text)
            syf4 = urlparse(text)
            syf5 = urlparse(text)
            replacement = ""
            nftfilename = str(os.path.basename(syf.path))
            print(nftfilename)
            if len(message.attachments) > 1:
               nftfilename2 = str(os.path.basename(syf2.path))
               print(nftfilename2)

            if len(message.attachments) > 1:
               text3 = nftfilename2
               size2 = len(text3)
            text2 = nftfilename
            size = len(text2)
            replacement2 = ""
            nftfilename76 = text2.replace(text2[size - 4:], replacement2)
            print(nftfilename76)
            if len(message.attachments) > 1:
               nftfilename77 = text3.replace(text3[size2 - 4:], replacement2)
               print(nftfilename77)
            for i in nfts:
                await asyncio.sleep(0.1)
                if not 'token' in str(i) and not 'nazwa' in str(i) and not 'cena' in str(i) and not 'sprzedarz' in str(i) and not 'kupiono' in str(i) and not 'authorid' in str(i) and not str(message.author.id) in str(i)  and not nfts[str(i)].isnumeric() and not len(nftfilename76) < 2 and not '.mp4' in nftfilename:
                    print(str(i))
                    imagenft = nfts[str(i)]
                    imagenfturl = urlparse(imagenft)
                    nftfilenamefromdatabasetocheckBRUH = str(os.path.basename(imagenfturl.path))
                    sizeBRUH = len(nftfilenamefromdatabasetocheckBRUH)
                    replacement3 = ""
                    nftfilenamefromdatabasetocheck = nftfilenamefromdatabasetocheckBRUH.replace(nftfilenamefromdatabasetocheckBRUH[sizeBRUH - 4:], replacement3)
                    print('\n' + nftfilenamefromdatabasetocheck + ' nazwa pliku nft sprawdzanego na serwerze' + '\n')
                    print(nftfilename76 + ' nazwa pliku w zalczniku bez rozszerzenia' + '\n')
                    if len(message.attachments) > 1:
                        print(nftfilename77 + ' nazwa pliku w zalczniku bez rozszerzenia drugiego' + '\n')

                    print(nftfilename + ' nazwa pliku w zalczniku' + '\n')

                    if len(message.attachments) > 1:
                       print(nftfilename2 + ' nazwa pliku w zalczniku' + '\n')
                    aicheckname = SequenceMatcher(None, str(nftfilenamefromdatabasetocheck).lower(), str(nftfilename76).lower())
                    print(str(aicheckname.ratio()) + ' procnt podobienstwa w nazwie' + '\n')
                    if len(message.attachments) > 1:
                        aicheckname2 = SequenceMatcher(None, str(nftfilenamefromdatabasetocheck).lower(), str(nftfilename77).lower())
                        print(str(aicheckname2.ratio()) + ' procnt podobienstwa w nazwie w 2' + '\n')
                    if  not 'https://tenor.com' in messageContent:
                        hash0 = imagehash.average_hash(Image.open(requests.get(imagenft, stream=True).raw))
                        hash1 = imagehash.average_hash(Image.open(requests.get(text, stream=True).raw))
                        cutoff = 5  # maximum bits that could be different between the hashes.
                        if hash0 - hash1 < cutoff and not 'https://tenor.com' in messageContent:
                          print('obrazek jest podobny wygladowo')
                          silamrityinviewimage = 1
                          print(str(hash0 - hash1))
                        else:
                          print('obrazek nie jest podobny wygladowo')
                          silamrityinviewimage = 0
                          print(str(hash0 - hash1))
                    if len(message.attachments) > 1:
                        if  not 'https://tenor.com' in messageContent:
                            hash2 = imagehash.average_hash(Image.open(requests.get(imagenft, stream=True).raw))
                            hash3 = imagehash.average_hash(Image.open(requests.get(file2, stream=True).raw))
                            cutoff = 5  # maximum bits that could be different between the hashes.
                            if hash2 - hash3 < cutoff and not 'https://tenor.com' in messageContent:
                              print('obrazek jest podobny wygladowo')
                              silamrityinviewimage2 = 1
                              print(str(hash2 - hash3))
                            else:
                              print('obrazek nie jest podobny wygladowo')
                              silamrityinviewimage2 = 0
                              print(str(hash2 - hash3))

                    silmaritypercentage = aicheckname.ratio()
                    if len(message.attachments) > 1:
                       silmaritypercentage2 = aicheckname2.ratio()
                    await asyncio.sleep(0.1)
                    if (str(nftfilename.lower()) in str(nfts[str(i)]).lower()) or (str(nftfilename76.lower()) in str(nfts[str(i)]).lower()) or (silmaritypercentage > 0.69) or (silamrityinviewimage == 1):
                        await asyncio.sleep(0.1)
                        nfttokenfrommessage = str(i).replace(' image','')
                        await asyncio.sleep(0.1)
                        print(nfttokenfrommessage + ' token znalzeiony w przeslanym pliku! <---------------------------------------- ' + nftfilename)
                        if nfts[str(nfttokenfrommessage) + ' authorid'] == str(message.author.id):
                            currentusernfts.append(nfttokenfrommessage + str(message.author.id))
                            print(str(message.author.name) + ' posiada nft jako autor: ' + nfttokenfrommessage)
                        for i in nftowners:
                            if str(nfttokenfrommessage) + ' ' + str(message.author.id) in i:
                                print(str(message.author.name) + ' posiada nft kupione: ' + i)
                                currentusernfts.append(i)
                    if len(message.attachments) > 1:
                        if (str(nftfilename2.lower()) in str(nfts[str(i)]).lower()) or (str(nftfilename77.lower()) in str(nfts[str(i)]).lower()) or (silmaritypercentage2 > 0.69) or (silamrityinviewimage2 == 1):
                            await asyncio.sleep(0.1)
                            nfttokenfrommessage = str(i).replace(' image','')
                            await asyncio.sleep(0.1)
                            print(nfttokenfrommessage + ' token znalzeiony w przeslanym pliku! <---------------------------------------- ' + nftfilename)
                            if nfts[str(nfttokenfrommessage) + ' authorid'] == str(message.author.id):
                                currentusernfts.append(nfttokenfrommessage + str(message.author.id))
                                print(str(message.author.name) + ' posiada nft jako autor: ' + nfttokenfrommessage)
                            for i in nftowners:
                                if str(nfttokenfrommessage) + ' ' + str(message.author.id) in i:
                                    print(str(message.author.name) + ' posiada nft kupione: ' + i)
                                    currentusernfts.append(i)
            if not nfttokenfrommessage == '' or nfttokenfrommessage == ' ':
                print('token istenije mozna dac grzywne!')
            if nfttokenfrommessage == '' or nfttokenfrommessage == ' ':
                print('token nie istenieje w tym pliku!')
            await asyncio.sleep(0.1)
            if currentusernfts == [] and not str(message.author.id) == '903986696658518056' and not nfttokenfrommessage == '' and not nfttokenfrommessage == ' ':
                amount = 1
                print(member.name + ' grzywna !!!!')
                if str(member.id) + ' kasa' in amounts:
                    print('jest')
                    if amounts[str(member.id) + ' kasa'] >= 1:
                        amount = 1
                        amounts[str(member.id) + ' kasa'] -= amount
                        tworcanft = await client.fetch_user(nfts[str(nfttokenfrommessage) + ' authorid'])
                        embed = discord.Embed(title="Grzywna!!!", description=str(member.display_name) + ' Został poddany karze grzywny w wysokości ' + str(amount) + ' social credit za wysyłanie NFT autorstwa '+ str(tworcanft.name) +' bez posiadania go!' +'\n' +'\n' + ' Token: ' + str(nfttokenfrommessage), colour=discord.Color.red())
                        embed.set_thumbnail(url = random.choice(creditplusimages))
                        message4 = await message.channel.send(embed=embed)
                        _save()
                        await asyncio.sleep(1)
                        _upload()
            currentusernfts = []
            nfttokenfrommessage = ''
            silmaritypercentage = None
            silamrityinviewimage = 0












    await client.process_commands(message)

@client.command()
async def listaskazanych(ctx):
    global gulagmembers
    hell = discord.utils.find(lambda r: r.name == 'PszczelarzHell', ctx.guild.roles)

    await ctx.message.delete()
    for guild in client.guilds:
            for member in ctx.guild.members:
                if not member.display_name in gulagmembers:
                    if hell in member.roles:
                        gulagmembers.append(member.display_name)
                        print(gulagmembers)
    gulagmembers.sort()
    wfinaltext = str(gulagmembers).replace('[','')
    wfinaltext2 = str(wfinaltext).replace(']','')
    wfinaltext3 = str(wfinaltext2).replace("'",'')
    wfinaltext4 = str(wfinaltext3).replace(",",', \n')
    print(wfinaltext4)
    embed = discord.Embed(title="Aktualnie w gułagu", description= wfinaltext4) #,color=Hex code
    await ctx.send(embed=embed)
    gulagmembers = []



@client.command(pass_context=True)
async def kupodwiedzinywgulagu(ctx):
    amount = 30
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    else:
        amounts[primary_id] -= amount
        viprank = discord.utils.find(lambda r: r.name == 'Gulag odwiedziny', ctx.guild.roles)
        await ctx.message.author.add_roles(viprank)
        embed = discord.Embed(title="Zakupiono 10 minut odwiedzin w gułagu!", description=str(ctx.message.author.display_name) + ' Otrzymał 10 minut wstępu do gułagu bez restrykcji za ' + str(amount) + ' social credit!', colour=discord.Color.red())
        embed.set_thumbnail(url = 'https://cdn-icons-png.flaticon.com/512/263/263142.png')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()
    await asyncio.sleep(600)
    viprank2 = discord.utils.find(lambda r: r.name == 'Gulag odwiedziny', ctx.guild.roles)
    await ctx.message.author.remove_roles(viprank2)
    embed = discord.Embed(title="Po Odwiedzinach!", description=str(ctx.message.author.display_name) + ' Wypierdalaj!', colour=discord.Color.red())
    embed.set_thumbnail(url = 'https://lh3.googleusercontent.com/proxy/nIVopvo-6xM_DEZBfwFfds6K0gl8axTtt0cvd_CvSMmPxoa2jlUy9t5bYE4z1IicMs87nIrDMOTGUI7BDXqveaSwWxhANRU')
    message4 = await ctx.send(embed=embed)

@client.command(pass_context=True)
@has_permissions(kick_members=True, ban_members=True)
async def gulag(ctx, amount: int, other: discord.Member):
    other_id2 = str(ctx.message.author.id)
    other_id = other_id2 + ' kasa'
    primary_id2 = str(other.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in amounts:
        await ctx.send("Gościu nie ma konta :( Musi się zarejestrować sc!zarejestruj albo sc!przymusowarejestracja")
    elif primary_id == '264079253757231104 kasa':
        await ctx.send("No co ty prezydenta??????")
    else:
        gulaggrzywna[primary_id] = amount
        viprank = discord.utils.find(lambda r: r.name == 'PszczelarzHell', ctx.guild.roles)
        await other.add_roles(viprank)
        embed = discord.Embed(title="Gułag!!!", description=str(other.display_name) + ' Został wtrącony do gułagu, z możliwością wyjścia za ' + str(amount) + ' social credit!', colour=discord.Color.red())
        embed.set_thumbnail(url = 'https://superhistoria.pl/_thumb/71/f6/8158f1c635bd1dc262fcfbc9f92d.jpeg')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()

@client.command(pass_context=True)
@has_permissions(kick_members=True, ban_members=True)
async def zwolnijzgulagu(ctx, other: discord.Member):
    other_id2 = str(ctx.message.author.id)
    other_id = other_id2 + ' kasa'
    primary_id2 = str(other.id)
    primary_id = primary_id2 + ' kasa'
    if primary_id not in gulaggrzywna:
        await ctx.send("Gościu nie ma konta :( Musi się zarejestrować sc!zarejestruj albo sc!przymusowarejestracja")
    else:
        gulaggrzywna[primary_id] = 0
        viprank = discord.utils.find(lambda r: r.name == 'PszczelarzHell', ctx.guild.roles)
        await other.remove_roles(viprank)
        embed = discord.Embed(title="Zwolniono z Gułagu!", description=str(other.display_name) + ' Został zwolniony z gułagu!', colour=discord.Color.green())
        embed.set_thumbnail(url = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTkBYb0cUnDJe5il3Qf9j-LxiBnGtqGU60NMw&usqp=CAU')
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    _save()
    await asyncio.sleep(1)
    _upload()


@client.command(pass_context=True)
async def nftcreate(ctx, nazwa: str ,token: str,cena: int):
    global nfts
    global nftowners
    amount = 200
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    primary_id3 = primary_id2 + ' nft'
    attachment = ctx.message.attachments[0]
    if primary_id not in amounts:
     await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < amount:
        await ctx.send("Nie można przetworzyć transakcji")
    elif attachment.url == "":
        await ctx.send("Nie ma obrazka bruh")
    else:
        if str(token) + ' token' in nfts:
            embed = discord.Embed(title="nft istnieje ❌ ", description=str(ctx.message.author.name)+ ' co ty chcesz!', colour=discord.Color.dark_red())
            embed.set_thumbnail(url = 'https://static.thenounproject.com/png/4340145-200.png')
            message4 = await ctx.send(embed=embed)
        if str(token) + ' token' not in nfts:
            nfts[str(token) + ' token'] = str(token)
            nfts[str(token) + ' image'] = str(attachment.url)
            nfts[str(token) + ' nazwa'] = str(nazwa)
            nfts[str(token) + ' cena'] = int(cena)
            nfts[str(token) + ' sprzedarz'] = 0
            nfts[str(token) + ' kupiono'] = 0
            nfts[str(token) + ' authorid'] = str(primary_id2)
            nfts[str(token) + ' ' + str(primary_id2)] = str(primary_id2)
            nftowners[str(token) + ' ' + str(primary_id2)] = int(cena)
            amounts[primary_id] -= amount
            embed = discord.Embed(title="Stworzono NFT!!", description=str(ctx.message.author.display_name) + ' Stworzył NFT: ' + str(nazwa) + '\n' +'Cena: ' + str(cena) + ' social credit' + '\n' +'Token: ' + str(token), colour=discord.Color.dark_orange())
            embed.set_thumbnail(url = str(attachment.url))
            message4 = await ctx.send(embed=embed)
            _save()
            await asyncio.sleep(1)
            _upload()



@client.command(pass_context=True)
async def nftbuy(ctx, token: str):
    global nfts
    global nftowners
    amount = nfts[str(token) + ' cena']
    print(amount)
    primary_id2 = str(ctx.message.author.id)
    primary_id = primary_id2 + ' kasa'
    primary_id3 = primary_id2 + ' nft'
    if primary_id not in amounts:
     await ctx.send("Nie masz konta!")
    elif amounts[primary_id] < int(amount):
        await ctx.send("Nie można przetworzyć transakcji")
    elif str(token) + ' ' + primary_id2 in nftowners:
        await ctx.send("Już posiadasz to NFT!")
    else:
        if not str(token) + ' token' in nfts:
            embed = discord.Embed(title="nft nie istnieje ❌ ", description=str(ctx.message.author.name)+ ' co ty chcesz!', colour=discord.Color.dark_red())
            embed.set_thumbnail(url = 'https://static.thenounproject.com/png/4340145-200.png')
            message4 = await ctx.send(embed=embed)
            await ctx.message.delete()
        if str(token) + ' token'  in nfts:
            amounts[primary_id] -= int(amount)
            amounts[str(nfts[str(token) + ' authorid'])  + ' kasa'] += (int(amount))
            nftowners[str(token) + ' ' + str(primary_id2)] = nfts[str(token) + ' cena']
            nfts[str(token) + ' kupiono']  += 1
            embed = discord.Embed(title="Kupiono NFT!!", description=str(ctx.message.author.display_name) + ' Kupił NFT: ' + str(nfts[str(token) + ' nazwa']) + '\n' +'Cena: ' + str(nfts[str(token) + ' cena']) + ' social credit' + '\n' +'Token: ' + str(nfts[str(token) + ' token']), colour=discord.Color.green())
            embed.set_thumbnail(url = str(nfts[str(token) + ' image']))
            message4 = await ctx.send(embed=embed)
            nfts[str(token) + ' cena'] += 100
            _save()
            await asyncio.sleep(1)
            _upload()
            await ctx.message.delete()



@client.command(pass_context=True)
async def nft(ctx, token: str):
    id2 = str(ctx.message.author.id)
    sale = ''
    if str(token) + ' token' in nfts:
        print(nfts[str(token) + ' authorid'])
        sprzedarz = nfts[str(token) + ' sprzedarz']
        if nfts[str(token) + ' sprzedarz'] == 0:
            sale = 'nie'
        embed = discord.Embed(title=nfts[str(token) + ' nazwa'], description='<@' + nfts[str(token) + ' authorid'] +'> ' + ' Stworzył to NFT' + '\n' +'Cena: ' + str(nfts[str(token) + ' cena']) + ' social credit' + '\n' +'Token: ' + nfts[str(token) + ' token'] + '\n' +'Promowane: ' + sale + '\n' +'Kupiono: ' + str(nfts[str(token) + ' kupiono']) + ' razy', colour=discord.Color.dark_orange())
        embed.set_thumbnail(url = nfts[str(token) + ' image'])
        message4 = await ctx.send(embed=embed)
        await ctx.message.delete()
    else:
        await ctx.send("Nie ma takiego nft!")



@client.command(pass_context=True)
async def mycreatednfts(ctx):
    global nfts
    global currentusernfts
    for i in nfts:
        print(i)
        if  str(ctx.message.author.id) in i:
            print(i + ' znaleziono autora to jego nft!')
            wfinaltext65 = str(i).replace(str(ctx.message.author.id),'')
            wfinaltext66 = str(wfinaltext65).replace(' ','')
            currentusernfts.append(wfinaltext66)
            print(currentusernfts)
    wfinaltext = str(currentusernfts).replace('[','')
    wfinaltext2 = str(wfinaltext).replace(']','')
    wfinaltext3 = str(wfinaltext2).replace("'",'')
    wfinaltext4 = str(wfinaltext3).replace(",",' \n')
    print(wfinaltext4)
    embed = discord.Embed(title=str(ctx.message.author.name) + " created Nft's" , description=wfinaltext4, colour=discord.Color.blue())
    embed.set_thumbnail(url = 'https://static.thenounproject.com/png/4340145-200.png')
    message4 = await ctx.send(embed=embed)
    await ctx.message.delete()
    currentusernfts = []



@client.command(pass_context=True)
async def mynfts(ctx):
    global nftowners
    global currentusernfts
    for i in nftowners:
        print(i)
        if  str(ctx.message.author.id) in i:
            print(i + ' znaleziono autora to jego nft!')
            wfinaltext65 = str(i).replace(str(ctx.message.author.id),'')
            wfinaltext66 = str(wfinaltext65).replace(' ','')
            currentusernfts.append(wfinaltext66)
            print(currentusernfts)
    wfinaltext = str(currentusernfts).replace('[','')
    wfinaltext2 = str(wfinaltext).replace(']','')
    wfinaltext3 = str(wfinaltext2).replace("'",'')
    wfinaltext4 = str(wfinaltext3).replace(",",' \n')
    print(wfinaltext4)
    embed = discord.Embed(title=str(ctx.message.author.name) + " Nft's" , description=wfinaltext4, colour=discord.Color.blue())
    embed.set_thumbnail(url = 'https://static.thenounproject.com/png/4340145-200.png')
    message4 = await ctx.send(embed=embed)
    await ctx.message.delete()
    currentusernfts = []



@client.command(pass_context=True)
async def nftshow(ctx, token: str):
    id2 = str(ctx.message.author.id)
    sale = ''
    if str(token) + ' token' in nfts:
        print(nfts[str(token) + ' authorid'])
        message4 = await ctx.send(nfts[str(token) + ' image'])
    else:
        await ctx.send("Nie ma takiego nft!")



@client.command(pass_context=True)
async def nftlist(ctx):
    global nfts
    global currentusernfts

    for i in nfts:
        print(i)
        if  "cena" in i:
            text2 = str(i)
            size = len(text2)
            replacement2 = ""
            token = text2.replace(text2[size - 5:], replacement2)
            print(token)
            userid = nfts[str(token) + " authorid"]
            print("user id " + str(userid))
            user = await client.fetch_user(userid)
            print(nfts[str(i)])
            currentusernfts.append('**' + str(nfts[str(token) + ' nazwa']) +'**,'+ str(nfts[str(i)]) + " Social Credit, Stworzono przez: " + user.name + ',' + 'Token: ' + str(token) + ',' +'Kupiono: ' + str(nfts[str(token) + ' kupiono']) + ' razy' + ',')
            print(currentusernfts)
            currentusernfts.sort()
    wfinaltext = str(currentusernfts).replace('[','')
    wfinaltext2 = str(wfinaltext).replace(']','')
    wfinaltext3 = str(wfinaltext2).replace("'",'')
    wfinaltext4 = str(wfinaltext3).replace(",",' \n')
    print(wfinaltext4)
    embed = discord.Embed(title="NFT list" , description=wfinaltext4, colour=discord.Color.blue())
    embed.set_thumbnail(url = 'https://static.thenounproject.com/png/4340145-200.png')
    message4 = await ctx.send(embed=embed)
    await ctx.message.delete()
    currentusernfts = []



client.run(os.environ['SOCIALCREDITBOT_TOKEN'])

