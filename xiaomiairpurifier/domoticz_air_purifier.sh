#!/usr/bin/env bash

# Get the data
data=$(/bin/node /etc/configuration/xiaomiairpurifier/airpurifier.js xiaomi_air_purifier_1 status)
# Sort it
temperature=$(echo "$data" | grep "temperature" | sed -e s/[^0-9.]//g)
humidity=$(echo "$data" | grep "humidity" | sed -e s/[^0-9.%]//g)
aqi=$(echo "$data" | grep "aqi" | sed -e s/[^0-9.]//g)

# Load it into Domoticz
curl -s "http://domoticz:8090/json.htm?type=command&param=udevice&idx=44&nvalue=0&svalue=${temperature};${humidity};0"
curl -s "http://domoticz:8090/json.htm?type=command&param=udevice&idx=45&svalue=${aqi}"

