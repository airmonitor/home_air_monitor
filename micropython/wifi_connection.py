import sys
from lib import logging
import connect_wifi
import utime
from constants import WIFI_PASSWORD, SSID

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(levelname)s]:%(name)s:%(message)s"))


def wifi_connect():
    """
    Connect to Wi-Fi
    """
    logging.info("Connecting to wifi...")
    connect_wifi.connect(ssid=SSID, password=WIFI_PASSWORD)
    utime.sleep(10)
    logging.info("Wifi connected")
