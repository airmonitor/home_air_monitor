#!/usr/bin/env bash

cd /etc/configuration/
curl -O https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/sds011.py
curl -O https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/smog_monitor.py
curl -O https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/bme280.py
curl -O https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/OTA1.sh
chmod +x *.py
chmod +x *.sh
/etc/configuration/OTA1.sh
