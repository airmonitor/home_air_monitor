#!/usr/bin/python3.4
#
# CCS811_RPi class usage example
#
# Petr Lukas
# July, 11 2017
#
# Version 1.0

import time  # comment this line if you don't need ThinkSpeak connection
import subprocess
from influxdb import InfluxDBClient
import base64
from configparser import ConfigParser
import urllib3
import json
from CCS811_RPi import CCS811_RPi
import time
urllib3.disable_warnings()



ccs811 = CCS811_RPi()
parser = ConfigParser()
parser.read('/etc/configuration/configuration.data')

voivodeship = (parser.get('airmonitor', 'voivodeship'))
city = (parser.get('airmonitor', 'city'))
street = (parser.get('airmonitor', 'street'))
box = (parser.get('airmonitor', 'box'))
placement = (parser.get('airmonitor', 'placement'))
lat = (parser.getfloat('airmonitor', 'lat'))
long = (parser.getfloat('airmonitor', 'long'))
sensor_model_co2 = (parser.get('airmonitor', 'sensor_model_co2'))

# Do you want to send data to thingSpeak? If yes set WRITE API KEY, otherwise set False
THINGSPEAK = False  # or type 'YOURAPIKEY'

# Do you want to preset sensor baseline? If yes set the value here, otherwise set False
INITIALBASELINE = False

# Do you want to use integrated temperature meter to compensate temp/RH (CJMCU-8118 board)?
# If not pre-set sensor compensation temperature is 25 C and RH is 50 %
# You can compensate manually by method ccs811.setCompensation(temperature,humidity) 
HDC1080 = False

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
pause = 6
start_iteration = 0
stop_iteration = 11


def thingSpeak(eCO2, TVOC, baseline, temperature, humidity):
    print('Sending to ThingSpeak API...')
    url = "https://api.thingspeak.com/update?api_key="
    url += THINGSPEAK
    url += "&field1="
    url += str(eCO2)
    url += "&field2="
    url += str(TVOC)
    url += "&field3="
    url += str(baseline)
    url += "&field4="
    url += str(temperature)
    url += "&field5="
    url += str(humidity)
    # print url
    try:
        content = urllib3.urlopen(url).read()
    except urllib3.HTTPError:
        print("Invalid HTTP response")
        return False
    print('Done')
    # print content


print('Checking hardware ID...')
hwid = ccs811.checkHWID()
if (hwid == hex(129)):
    print('Hardware ID is correct')
else:
    print('Incorrect hardware ID ', hwid, ', should be 0x81')

# print 'MEAS_MODE:',ccs811.readMeasMode()
ccs811.configureSensor(configuration)
print('MEAS_MODE:', ccs811.readMeasMode())
print('STATUS: ', bin(ccs811.readStatus()))
print('---------------------------------')

# Use these lines if you need to pre-set and check sensor baseline value
if (INITIALBASELINE > 0):
    ccs811.setBaseline(INITIALBASELINE)
    print(ccs811.readBaseline())

# Use these lines if you use CJMCU-8118 which has HDC1080 temp/RH sensor
if (HDC1080):
    hdc1000 = SDL_Pi_HDC1000.SDL_Pi_HDC1000()
    hdc1000.turnHeaterOff()
    hdc1000.setTemperatureResolution(SDL_Pi_HDC1000.HDC1000_CONFIG_TEMPERATURE_RESOLUTION_14BIT)
    hdc1000.setHumidityResolution(SDL_Pi_HDC1000.HDC1000_CONFIG_HUMIDITY_RESOLUTION_14BIT)

while (start_iteration < stop_iteration):
    if (HDC1080):
        humidity = hdc1000.readHumidity()
        temperature = hdc1000.readTemperature()
        ccs811.setCompensation(temperature, humidity)
    else:
        proc = subprocess.Popen('/etc/configuration/bme280.py.humidity', stdout=subprocess.PIPE)
        humidity = proc.stdout.read()
        humidity = float(humidity)

        proc = subprocess.Popen('/etc/configuration/bme280.py.temperature', stdout=subprocess.PIPE)
        temperature = proc.stdout.read()
        temperature = float(temperature)

    statusbyte = ccs811.readStatus()
    print('STATUS: ', bin(statusbyte))

    error = ccs811.checkError(statusbyte)
    if (error):
        print('ERROR:', ccs811.checkError(statusbyte))

    if (not ccs811.checkDataReady(statusbyte)):
        print('No new samples are ready')
        print('---------------------------------')
        time.sleep(pause)
        continue;
    result = ccs811.readAlg();
    if (not result):
        # print('Invalid result received')
        time.sleep(pause)
        continue;
    baseline = ccs811.readBaseline()

    json_body_public = [
        {
            "measurement": "CO2",
            "tags": {
                "voivodeship": voivodeship,
                "city": city,
                "street": street,
                "box": box,
                "placement": placement,
                "lat": lat,
                "long": long,
                "sensor": "0",
                "sensor_model": sensor_model_co2
            },
            "fields": {
                "value": float(result['eCO2'])
            }
        },
        {
            "measurement": "TVOC",
            "tags": {
                "voivodeship": voivodeship,
                "city": city,
                "street": street,
                "box": box,
                "placement": placement,
                "lat": lat,
                "long": long,
                "sensor": "0",
                "sensor_model": sensor_model_co2
            },
            "fields": {
                "value": float(result['TVOC'])
            }
        }
    ]
    client = InfluxDBClient(host='db.airmonitor.pl', port=(base64.b64decode("ODA4Ng==")),
                            username=(base64.b64decode("YWlybW9uaXRvcl9wdWJsaWNfd3JpdGU=")), password=(
            base64.b64decode("amZzZGUwMjh1cGpsZmE5bzh3eWgyMzk4eTA5dUFTREZERkdBR0dERkdFMjM0MWVhYWRm")),
                            database=(base64.b64decode("YWlybW9uaXRvcg==")), ssl=True, verify_ssl=False,
                            timeout=4)
    client.write_points(json_body_public)

    print('Temp: ', temperature, ' StC')
    print('Hum: ', humidity, ' %')
    print('eCO2: ', result['eCO2'], ' ppm')
    print('TVOC: ', result['TVOC'], 'ppb')
    print('Status register: ', bin(result['status']))
    print('Last error ID: ', result['errorid'])
    print('RAW data: ', result['raw'])
    print('Baseline: ', baseline)
    print('---------------------------------')

    if (THINGSPEAK is not False):
        thingSpeak(result['eCO2'], result['TVOC'], baseline, temperature, humidity)
    time.sleep(pause)
    start_iteration = start_iteration + 1
