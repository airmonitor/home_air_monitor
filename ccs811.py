#!/usr/bin/python3.4
#
# CCS811_RPi class usage example
#
# Petr Lukas
# July, 11 2017
#
# Version 1.0

import subprocess
from configparser import ConfigParser
import urllib3
from CCS811_RPi import CCS811_RPi
import time
import json
import requests
from bme280 import readBME280All
urllib3.disable_warnings()

temperature, pressure, humidity = readBME280All(addr=0x76)


ccs811 = CCS811_RPi()
parser = ConfigParser()
parser.read('/etc/configuration/configuration.data')
lat = (parser.getfloat('airmonitor', 'lat'))
long = (parser.getfloat('airmonitor', 'long'))
sensor = (parser.get('airmonitor', 'sensor_model_co2'))
co2_values = []
tvoc_values = []

INITIALBASELINE = False


'''
MEAS MODE REGISTER AND DRIVE MODE CONFIGURATION
0b0       Idle (Measurements are disabled in this mode)
0b10000   Constant power mode, IAQ measurement every second
0b100000  Pulse heating mode IAQ measurement every 10 seconds
0b110000  Low power pulse heating mode IAQ measurement every 60
0b1000000 Constant power mode, sensor measurement every 250ms
'''
# Set MEAS_MODE (measurement interval)
configuration = 0b10000

# Set read interval for retriveving last measurement data from the sensor
pause = 1
start_iteration = 0
stop_iteration = 29

print('Checking hardware ID...')
hwid = ccs811.checkHWID()
if hwid == hex(129):
    print('Hardware ID is correct')
else:
    print('Incorrect hardware ID ', hwid, ', should be 0x81')

ccs811.configureSensor(configuration)
print('MEAS_MODE:', ccs811.readMeasMode())
print('STATUS: ', bin(ccs811.readStatus()))
print('---------------------------------')

# Use these lines if you need to pre-set and check sensor baseline value
if INITIALBASELINE > 0:
    ccs811.setBaseline(INITIALBASELINE)
    print(ccs811.readBaseline())

while start_iteration < stop_iteration:
    humidity = float(humidity)
    temperature = float(temperature)
    print(humidity, temperature)

    statusbyte = ccs811.readStatus()
    print('STATUS: ', bin(statusbyte))

    error = ccs811.checkError(statusbyte)
    if error:
        print('ERROR:', ccs811.checkError(statusbyte))

    if not ccs811.checkDataReady(statusbyte):
        print('No new samples are ready')
        print('---------------------------------')
        time.sleep(pause)
        continue
    result = ccs811.readAlg()
    if not result:
        time.sleep(pause)
        continue
    baseline = ccs811.readBaseline()

    print('Temp: ', temperature, ' StC')
    print('Hum: ', humidity, ' %')
    print('eCO2: ', result['eCO2'], ' ppm')
    print('TVOC: ', result['TVOC'], 'ppb')
    print('Status register: ', bin(result['status']))
    print('Last error ID: ', result['errorid'])
    print('RAW data: ', result['raw'])
    print('Baseline: ', baseline)
    print('---------------------------------')

    if result['eCO2'] >= 400:
        co2_values.append(result['eCO2'])

    tvoc_values.append(result['TVOC'])

    time.sleep(pause)
    start_iteration += 1

print("\n\n\nList of CO2 values from sensor", co2_values)
co2_values_avg = (sum(co2_values) / len(co2_values))
print("CO2 Average: ", co2_values_avg)
print(co2_values)

print("\n\n\nList of TVOC values from sensor", tvoc_values)
tvoc_values_avg = (sum(tvoc_values) / len(tvoc_values))
print("TVOC Average: ", tvoc_values_avg)

data = {
    "lat": str(lat),
    "long": str(long),
    "co2": str(float('%.2f' % co2_values_avg)),
    "tvoc": str(float('%.2f' % tvoc_values_avg)),
    "sensor": sensor
}

url = 'http://api.airmonitor.pl:5000/api'
resp = requests.post(url, timeout=10, data=json.dumps(data), headers={"Content-Type": "application/json"})
print("Response code from AirMonitor API {}", resp.status_code)
