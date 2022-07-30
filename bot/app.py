import discord
import asyncio
import requests
from wakeonlan import send_magic_packet
from discord.ext.commands import Bot
from discord.ext import commands
import json
from datetime import date, datetime
from dateutil import tz
import os
import utils as u
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
HYPERVISOR_IP = os.getenv("HYPERVISOR_IP")
HYPERVISOR_MAC = os.getenv("HYPERVISOR_MAC")
INSTANCE_IP = os.getenv("INSTANCE_IP")
MC_SERVER_IP = os.getenv("MC_SERVER_IP")
PREFIX = "."
TIMEZONE = os.getenv("TIMEZONE")

SERVER_API_ENDPOINT = "http://" + INSTANCE_IP + ":8080"

timezone = tz.gettz(TIMEZONE)

bot = commands.Bot(command_prefix=PREFIX, description=":3c")

class states(Enum):
    OFF = 0
    STARTING = 1
    FAILED = 2
    RUNNING  = 2
    UNKNOWN = 3

hypervisor_status = states.OFF
instance_status = states.OFF
server_status = states.OFF
instance_api_status = states.OFF
host_api = states.OFF

def check_status():
    global hypervisor_status
    global instance_api_status
    global instance_status
    global server_status

    hypervisor_response = u.ping(HYPERVISOR_IP)

    if hypervisor_response is not True:
        print("Server is off")
        hypervisor_status = states.OFF
        return
    
    hypervisor_status = states.RUNNING

    instance_response = u.ping(INSTANCE_IP)
    if instance_response is not True:
        print("Instance is off")
        instance_status = states.OFF
        return

    instance_status = states.RUNNING

    try:
        print("Trying api")
        response = requests.get("http://" + INSTANCE_IP + ":8080/service_health")
        response = response.json()

        if response["server_status"] == True:
            print("Server is running")
            server_status = states.RUNNING

    except Exception as e:
        server_status = states.OFF
        print(e)




@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name=":cacopog:"))
    print(f"{bot.user} ready!")

@bot.command(brief="C ao6")
async def xD(ctx):
    await ctx.send("xD")

@bot.command(brief=":3c")
async def getip(ctx):
    await ctx.send(MC_SERVER_IP)

@bot.command()
async def stats(ctx):
    if server_status == states.OFF:
        await ctx.send("El server está apagado")

    response = requests.get(SERVER_API_ENDPOINT + "/stats").json()

    playerCount = response["player_count"]
    maxPlayers = response["max_players"]
    player_list = response["list"]
    str_list = "\r\n".join(player_list)
    cpuUsage = response["cpu_percent"]
    cpuCores = response["cores"]
    memUsage = response["memory"]
    dump = response["cpu_dump"]

    msg = f"**Qué ta chendo?🤨**\n"
    msg += f"{playerCount} de {maxPlayers} chibolos\n\n"
    msg += str_list
    msg += f"\n\n**Info de la machine 🤖**\n"
    msg += f"CPU : { cpuUsage }% | { cpuCores } cores\n"
    msg += f"Memoria : { memUsage }%\n"
    
    await ctx.send(msg)

@bot.command()
async def start(ctx):
    check_status()
    if server_status == states.RUNNING:
        await ctx.send("El sv ta up 🤨")
    if hypervisor_status == states.OFF:
        await ctx.send("Prendiendo server!")
        send_magic_packet(HYPERVISOR_MAC)
    
@bot.command()
async def shutdown(ctx):
    check_status()
    if server_status != states.OFF:

        response = requests.get(SERVER_API_ENDPOINT + "/stats").json()

        playerCount = response["player_count"]
        player_list = response["list"]
        str_list = "\r\n".join(player_list)
        if playerCount > 0:
            await ctx.send("No se puede apagar el server mientras hay chibolos conectados\n" + str_list)
            return
        requests.post("http://" + HYPERVISOR_IP + ":8080/shutdown")
        await ctx.send("Señal enviada xD")

check_status()
bot.run(TOKEN)