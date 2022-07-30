import json
import os
import psutil
from mcrcon import MCRcon
from bottle import route, run, request, post, get
import os
from dotenv import load_dotenv

load_dotenv()

SERVER = os.getenv("SERVER")
PASSWORD = os.getenv("PASSWORD")

def get_server_stats():
    return {
        "cpu_percent" : psutil.cpu_percent(),
        "cores" : psutil.cpu_count(),
        "memory" : psutil.virtual_memory().percent,
        "cpu_dump" : psutil.cpu_stats()
    }

def get_players():
    with MCRcon(SERVER, PASSWORD) as mcr:   
        response = mcr.command("/list").replace(",", "")
        playerCount = response.split(" ")[2]
        maxPlayers = response.split(" ")[7]
        players = response.split(" ")[10:]

        stats = {
            "player_count" : int(playerCount),
            "max_players" : int(maxPlayers),
            "list" : players 
        }

        return stats

@get("/stats")
def players():
    playerStats = get_players()
    serverStats = get_server_stats()
    
    stats = {}
    stats = playerStats | serverStats

    return stats

@post("/execute")
def execute():
    data = request.json

    cmd = data["cmd"]

    with MCRcon(SERVER, PASSWORD) as mcr:   
        response = mcr.command("/" + cmd)

    return "ok"

@get("/service_health")
def service_health():
    serviceStatus = os.system("systemctl is-active --quiet mcserver")
    if serviceStatus > 0:
        return {
            "server_status" : False
        }
    return {
        "server_status" : True
    }


run(host="0.0.0.0", debug=True)