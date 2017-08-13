#!/usr/bin/env bash

cd /etc/configuration/
/usr/bin/curl -O https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/sds011.py
/usr/bin/curl -O https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/smog_monitor.py
/usr/bin/curl -O https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/bme280.py
/usr/bin/curl -O https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/OTA1.sh
/bin/chmod +x *.py
/bin/chmod +x *.sh
/etc/configuration/OTA1.sh
