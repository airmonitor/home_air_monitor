import network
from lib import logging

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(levelname)s]:%(name)s:%(message)s"))


def connect(ssid, password):
    station = network.WLAN(network.STA_IF)

    if station.isconnected():
        print("Already connected")
        return True

    station.active(True)
    station.connect(ssid, password)

    while not station.isconnected():
        pass

    logging.info("Connection successful")
    logging.info(station.ifconfig())
