#!/usr/bin/python3.4
#coding: utf-8

import time
from influxdb import InfluxDBClient
from sds011 import SDS011
import os
import base64
from configparser import ConfigParser
import urllib3

parser = ConfigParser(allow_no_value=False)
parser = ConfigParser()
parser.read('/etc/configuration/configuration.data')
sensor_model=(parser.get('airmonitor', 'sensor_model'))
lat=(parser.get('airmonitor', 'lat'))
long=(parser.get('airmonitor', 'long'))
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
sensor = SDS011('/dev/ttyAMA0')

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

os.system('rm /mnt/ramdisk_ram0/ppm10_average_sensor0')
os.system('rm /mnt/ramdisk_ram0/ppm25_average_sensor0')

count = 0
while (count < 30):

	values = sensor.get_values()
	print("Values measured: PPM10:", values[0], "PPM2.5:", values[1])
	count = count + 1
	time.sleep(1)

	f_average_PM10 = open('/mnt/ramdisk_ram0/ppm10_average_sensor0', 'a')
	ppm10 = str(values[0])
	f_average_PM10.write(ppm10 + '\n')
	f_average_PM10.close()

	f_average_PM25 = open('/mnt/ramdisk_ram0/ppm25_average_sensor0', 'a')
	ppm25 = str(values[1])
	f_average_PM25.write(ppm25 + '\n')
	f_average_PM25.close()

##PM10 Average##
total_PM10 = 0.0
length_PM10 = 0.0
infile = open('/mnt/ramdisk_ram0/ppm10_average_sensor0', 'r')
contents_PM10 = infile.read().strip().split()
for num in contents_PM10:
	amount = float(num)
	total_PM10 += amount
	length_PM10 = length_PM10 + 1
average_PM10 = total_PM10 / len(contents_PM10)
average_PM10 = (format(average_PM10, ',.2f'))
average_PM10 = float(average_PM10)
print("Average PM10 from 30 last measurements: ", average_PM10)
infile.close()

##PM25 Average##
total_PM25 = 0.0
length_PM25 = 0.0
infile = open('/mnt/ramdisk_ram0/ppm25_average_sensor0', 'r')
contents_PM25 = infile.read().strip().split()
for num in contents_PM25:
	amount = float(num)
	total_PM25 += amount
	length_PM25 = length_PM25 + 1
average_PM25 = total_PM25 / len(contents_PM25)
average_PM25 = (format(average_PM25, ',.2f'))
average_PM25 = float(average_PM25)
print("Average PM25 from 30 last measurements: ", average_PM25)
infile.close()

json_body_public = [
	{
		"measurement": "ppm25",
		"tags": {
			"lat": lat,
			"long": long,
			"sensor_model": sensor_model
		},
		"fields": {
			"value": average_PM25
		}
	},
	{
		"measurement": "ppm10",
		"tags": {
			"lat": lat,
			"long": long,
			"sensor_model": sensor_model
		},
		"fields": {
			"value": average_PM10
		}
	}
]


client = InfluxDBClient(host='db.airmonitor.pl', port=(base64.b64decode("ODA4Ng==")), username=(base64.b64decode("YWlybW9uaXRvcl9wdWJsaWNfd3JpdGU=")), password=(base64.b64decode("amZzZGUwMjh1cGpsZmE5bzh3eWgyMzk4eTA5dUFTREZERkdBR0dERkdFMjM0MWVhYWRm")), database=(base64.b64decode("YWlybW9uaXRvcg==")), ssl=True, verify_ssl=False, timeout=10)
client.write_points(json_body_public)

sensor.workstate = SDS011.WorkStates.Sleeping
