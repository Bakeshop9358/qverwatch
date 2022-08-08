import discord
import asyncio
from discord.ext.commands import Bot
from discord.ext import commands, tasks
import json
from datetime import date, datetime
from dateutil import tz
from dateutil.relativedelta import relativedelta
import os
import sys
from enum import Enum
from dotenv import load_dotenv
import logging
from Server import ServerController, states

logger =logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logging.basicConfig(level=logging.INFO)

handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)

load_dotenv()

TOKEN = os.getenv("TOKEN")
HYPERVISOR_IP = os.getenv("HYPERVISOR_IP")
HYPERVISOR_MAC = os.getenv("HYPERVISOR_MAC")
INSTANCE_IP = os.getenv("INSTANCE_IP")
MC_SERVER_IP = os.getenv("MC_SERVER_IP")
PREFIX = "."
MAX_EMPTY_TIME = 25
SERVER_API_ENDPOINT = "http://" + INSTANCE_IP + ":8080"

_TIMEZONE = os.getenv("TIMEZONE")
TIMEZONE = tz.gettz(_TIMEZONE)

bot = commands.Bot(command_prefix=PREFIX, description=":3c")

server = ServerController(host_ip=HYPERVISOR_IP, instance_ip=INSTANCE_IP, host_mac=HYPERVISOR_MAC)

last_alert_sent = datetime.now(tz=TIMEZONE)
do_not_stop_until = datetime.now(tz=TIMEZONE)

#TODO: Cambios persistentes
lock_id = None
watchlist = []

async def set_status():
    icon = "🟢"
    if lock_id != None:
        icon = "🔒"

    if server.server_status != states.RUNNING:
        return await bot.change_presence(activity=discord.Game(name="💀"))
    elif server.server_status == states.RUNNING:

        til_death = MAX_EMPTY_TIME - (datetime.now(tz=TIMEZONE) - server.last_time_with_players).total_seconds() / 60
        if til_death < 0:
            til_death = 0
        base_status = f"{icon} { server.stats.playerCount }/{ server.stats.maxPlayers } 🐀"
        if server.stats.playerCount == 0:
            icon = "🟡"
            base_status += f" { round(til_death, 1)} minutos restantes"

        return await bot.change_presence(activity=discord.Game(name=base_status))

@bot.event
async def on_ready():
    await set_status()
    check_health.start()
    logger.info(f"{bot.user} ready!")

@bot.command(brief="C ao6")
async def xD(ctx):
    await ctx.send("xD")
    await ctx.message.add_reaction("❎")
    await ctx.message.add_reaction("🇩")

@bot.command(brief=":3c")
async def getip(ctx):
    await ctx.send(MC_SERVER_IP)

@bot.command()
async def lock(ctx):
    global lock_id

    if lock_id != None:
        return await ctx.send(f"Ya existe un bloqueo.")
    
    lock_id = ctx.channel.id
    return await ctx.message.add_reaction("🔒")

@bot.command()
async def unlock(ctx):
    global lock_id
    if lock_id == None:
        return await ctx.send("No existe un bloqueo actual.")

    if ctx.channel.id == lock_id:
        lock_id = None
        return await ctx.message.add_reaction("✅")

    return await ctx.message.add_reaction("❌")    

@bot.command()
async def stats(ctx):
    
    stats = server.get_status()
    if stats.isRunning is False:
        await ctx.message.add_reaction("🤨")
        return await ctx.send("El server está apagado")

    idle_time_str = ""
    if stats.currentIdleTime < 0:
        idle_time_str = f"En configuración"
    else:
        idle_time_str = f"{ round(stats.currentIdleTime, 2) } actualmente"
        
    msg = f"**Qué ta chendo?🤨**\n"
    msg += f"{stats.playerCount} de {stats.maxPlayers} chibolos\n\n"
    msg += stats.get_string_list()
    msg += f"\n**Info de la machine 🤖**\n"
    msg += f"CPU : { stats.cpuUsage }% | { stats.cpuCores } cores\n"
    msg += f"Memoria : { stats.memoryPercent }%\n"
    msg += f"**Tiempo máximo de inactividad**: {MAX_EMPTY_TIME} minutos ({ idle_time_str }) "
    
    await ctx.send(msg)

@bot.command()
async def start(ctx):
    global do_not_stop_until

    if lock_id != None:
        return await ctx.send(f"xD")

    do_not_stop_until = datetime.now(tz=TIMEZONE) + relativedelta(minutes=5)
    server.last_time_with_players = do_not_stop_until
    
    logger.info(f"Agregado tiempo de gracia hasta {do_not_stop_until}")
    if check_health.is_running() is False:
        logger.info("La tarea no está corriendo")
        check_health.start()
    response = server.start_server()
    if response is True:
        return await ctx.message.add_reaction("✅")

    await ctx.message.add_reaction("🤨")
    return
    
@bot.command()
async def shutdown(ctx):

    if lock_id != None:
        return await ctx.send(f"No se puede ahora 🤨")

    server.get_status()
    if server.stats.playerCount > 0:
        return await ctx.send("No se puede apagar el server con chibolos conectados:\n" + server.stats.get_string_list())
    
    response = server.shutdown()
    if response:
        return await ctx.message.add_reaction("✅")

    return await ctx.message.add_reaction("❌")

def add_subscription(channel_id):
    global watchlist
    if channel_id not in watchlist:
        watchlist.append(channel_id)
        return True
    return False

@bot.command()
async def subscribe(ctx):
    add_subscription(ctx.channel.id)
    await ctx.message.add_reaction("✅")

@bot.command()
async def set_idle_time(ctx, arg1):
    global MAX_EMPTY_TIME
    try:
        MAX_EMPTY_TIME = int(arg1)
        await set_status()
        return await ctx.message.add_reaction("👌")
    except ValueError:
        return await ctx.message.add_reaction("🤨")
    

@tasks.loop(seconds=30)
async def check_health():
    global last_alert_sent
    server.get_status()
    await set_status()

    if server.stats.playerCount == 0:
        idle_time = (datetime.now(tz=TIMEZONE) - server.last_time_with_players).total_seconds() / 60 
        time_from_last_alert = (datetime.now(tz=TIMEZONE) - last_alert_sent ).total_seconds() / 60
        logger.info(f"{idle_time} minutos sin players, {time_from_last_alert} sin notificar, no detener hasta { do_not_stop_until } vs { datetime.now(tz=TIMEZONE) }")
        if idle_time > MAX_EMPTY_TIME and time_from_last_alert > MAX_EMPTY_TIME and do_not_stop_until > datetime.now(tz=TIMEZONE): # Para evitar spam 
            last_alert_sent = datetime.now(tz=TIMEZONE)
            if lock_id == None:
                for id in watchlist:
                    channel = await bot.fetch_channel(id)
                    await channel.send(f"Sv vacío por más de { MAX_EMPTY_TIME} minutos, apagando.")
                logger.warning("Apagando servidor por inactividad")
                server.shutdown()

        

bot.run(TOKEN)
