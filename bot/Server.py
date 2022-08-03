from enum import Enum
from utils import ping
from datetime import date, datetime
from dateutil import tz
import requests
import logging
import os
from wakeonlan import send_magic_packet

_TIMEZONE = os.getenv("TIMEZONE")
TIMEZONE = tz.gettz(_TIMEZONE)

class states(Enum):
    OFF = 0
    STARTING = 1
    FAILED = 2
    RUNNING  = 2
    UNKNOWN = 3

class ServerStats:
    players: list
    maxPlayers: int
    playerCount: int
    isRunning: bool
    maxIdleTime: int
    currentIdleTime: float
    cpuUsage: float
    cpuCores: int
    memoryPercent: float

    def __init__(self) -> None:
        pass

    def get_string_list(self)->str:
        return "\r\n".join(self.players)

class ServerController:

    host_ip: str = "0.0.0.0"
    host_mac: str
    instance_ip: str
    instance_api_address: str
    hypervisor_status = states.OFF
    instance_status = states.OFF
    server_status = states.OFF
    instance_api_status = states.OFF
    host_api = states.OFF
    stats = ServerStats

    last_time_with_players = datetime.now(tz=TIMEZONE)

    def __init__(self, host_ip, instance_ip, host_mac) -> None:
        self.host_ip = host_ip
        self.instance_ip = instance_ip
        self.instance_api_address = "http://" + instance_ip + ":8080"
        self.host_mac = host_mac
        pass

    def check_status(self):
        if ping(self.host_ip) is False:
            self.hypervisor_status = states.OFF
            self.instance_status = states.OFF
            self.server_status = states.OFF
            self.instance_api_status = states.OFF
            self.host_api = states.OFF

            return

        self.hypervisor_status = states.RUNNING
        self.host_api = states.RUNNING

        if ping(self.instance_ip) is False:
            self.instance_api_status = states.OFF
            self.instance_status = states.OFF
            self.server_status = states.OFF

            return
        
        self.instance_status = states.RUNNING

        try:
            response = requests.get(self.instance_api_address + "/service_health").json()
            if response["server_status"] is True:
                self.server_status = states.RUNNING
                self.instance_api_status = states.RUNNING
        except Exception as e:
            logging.warning(e)
            self.server_status = states.OFF
            self.instance_api_status = states.OFF

    def start_server(self)->bool:
        self.check_status()
        if self.hypervisor_status != states.RUNNING:
            send_magic_packet(self.host_mac)

            return True
        
        return False

    def get_status(self)->ServerStats:
        self.check_status()
        serverStats = ServerStats()
        if self.instance_status != states.RUNNING:
            serverStats.isRunning = False
            return serverStats

        response = requests.get(self.instance_api_address + "/stats").json()

        serverStats.playerCount = response["player_count"]
        serverStats.maxPlayers = response["max_players"]
        serverStats.players = response["list"]
        serverStats.cpuUsage = response["cpu_percent"]
        serverStats.cpuCores = response["cores"]
        serverStats.memoryPercent = response["memory"]
        serverStats.isRunning = True

        self.stats = serverStats
        if serverStats.playerCount > 0:
            self.last_time_with_players = datetime.now(tz=TIMEZONE)

        serverStats.currentIdleTime = (datetime.now(tz=TIMEZONE) - self.last_time_with_players).total_seconds() / 60 

        return serverStats

    def shutdown(self)->bool:
        if self.hypervisor_status != states.OFF:
            requests.post("http://" + self.host_ip + ":8080/shutdown")
            return True
        return False