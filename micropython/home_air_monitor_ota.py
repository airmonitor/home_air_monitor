import micropython_ota


def ota_updater():
    ota_host = 'https://static.airmonitor.pl'
    project_name = 'home_air_monitor_micropython'
    filenames = [
        "bme280.py",
        "bme680.py",
        "bme680_constants.py",
        "ccs811.py",
        "connect_wifi.py",
        "home_air_monitor_ota.py",
        "i2c.py",
        "micropython_ota.py",
        "pms7003.py",
        "ptqs1005.py",
        "sds011.py",
    ]

    micropython_ota.ota_update(
        ota_host,
        project_name,
        filenames,
        use_version_prefix=True,
        hard_reset_device=True,
        soft_reset_device=False,
        timeout=5
    )
