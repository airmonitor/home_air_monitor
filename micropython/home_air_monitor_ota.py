import micropython_ota


def ota_updater():
    ota_host = 'https://static.airmonitor.pl'
    project_name = 'home_air_monitor_micropython'
    filenames = ['ptqs1005.py']

    micropython_ota.ota_update(
        ota_host,
        project_name,
        filenames,
        use_version_prefix=True,
        hard_reset_device=True,
        soft_reset_device=False,
        timeout=5
    )
