#!/usr/bin/python3.4
# coding: utf-8

import time
from sds011 import SDS011
from configparser import ConfigParser
import urllib3
import json
import requests

parser = ConfigParser()
parser.read('/etc/configuration/configuration.data')
sensor = (parser.get('airmonitor', 'sensor_model'))
lat = (parser.get('airmonitor', 'lat'))
long = (parser.get('airmonitor', 'long'))
urllib3.disable_warnings()

# Nie zmieniaj niczego poniżej tej linii!##
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
#####################################################
# Create an instance of your sensor
sensor = SDS011('/dev/ttyUSB0')

# Now we have some details about it
print(sensor.device_id)
print(sensor.firmware)
print(sensor.dutycycle)
print(sensor.workstate)
print(sensor.reportmode)
# Set dutycyle to nocycle (permanent)
sensor.reset()
sensor.workstate = SDS011.WorkStates.Measuring
time.sleep(30)


COUNT = 0
FACTOR = 1.5
pm25_values = []
pm10_values = []

while COUNT < 30:

    values = sensor.get_values()
    print("Values measured: PPM10:", values[0], "PPM2.5:", values[1])
    pm25_values.append(values[1])
    pm10_values.append(values[0])
    COUNT += 1
    time.sleep(1)


print("List of PM2,5 values from sensor", pm25_values)
pm25_values_avg = (sum(pm25_values) / len(pm25_values))
print("PM2,5 Average", pm25_values_avg)

for i in pm25_values:
    if pm25_values_avg > i * 1.5:
        pm25_values.remove(max(pm25_values))
        pm25_values_avg = (sum(pm25_values) / len(pm25_values))
        print("Something is not quite right, some PM2,5 value is by 50% than average from last 9 measurements\n")
    elif pm25_values_avg < i * FACTOR:
        print("OK")
print(pm25_values)

print("List of PM10 values from sensor", pm10_values)
pm10_values_avg = (sum(pm10_values) / len(pm10_values))
print("PM10 Average", pm10_values_avg)

for i in pm10_values:
    if pm10_values_avg > i * FACTOR:
        pm10_values.remove(max(pm10_values))
        pm10_values_avg = (sum(pm10_values) / len(pm10_values))
        print("Something is not quite right, some value PM10 value is by 50% than average from last 9 measurements\n")
    elif pm10_values_avg < i * FACTOR:
        print("OK")
print(pm10_values)


data = '{"lat": "' + str(lat) + '", ' \
        '"long": "'+ str(long) + '", ' \
        '"pm25": ' + str(float('%.2f' % pm25_values_avg)) + ', ' \
        '"pm10":' + str(float('%.2f' % pm10_values_avg)) + ', ' \
        '"sensor": "' + str(sensor) + '"}'

url = 'http://api.airmonitor.pl:5000/api'
resp = requests.post(url,
                     timeout=10,
                     data=json.dumps(data),
                     headers={"Content-Type": "application/json"})
resp.status_code

sensor.workstate = SDS011.WorkStates.Sleeping

