import sys
from lib import logging
import micropython_ota

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(levelname)s]:%(name)s:%(message)s"))


def ota_updater():
    ota_host = 'https://static.airmonitor.pl'
    project_name = 'home_air_monitor_micropython'
    filenames = [
        "bme280.py",
        "bme680.py",
        "bme680_constants.py",
        "boot.py",
        "ccs811.py",
        "connect_wifi.py",
        "errors.py",
        "home_air_monitor_ota.py",
        "i2c.py",
        "micropython_ota.py",
        "pms7003.py",
        "ptqs1005.py",
        "sds011.py",
        "wifi_connection.py",
    ]
    logging.info("Starting OTA updater")

    micropython_ota.ota_update(
        ota_host,
        project_name,
        filenames,
        use_version_prefix=True,
        hard_reset_device=True,
        soft_reset_device=False,
        timeout=5
    )
    logging.info("OTA finished")
