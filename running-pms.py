#!/usr/bin/python3.4
# coding: utf-8

import serial
import datetime
import time
from influxdb import InfluxDBClient
import base64
from configparser import ConfigParser
import urllib3

parser = ConfigParser(allow_no_value=False)
parser.read('/etc/configuration/configuration.data')
pms_sensor_model=(parser.get('airmonitor', 'pms_sensor_model'))
lat=(parser.get('airmonitor', 'lat'))
long=(parser.get('airmonitor', 'long'))
urllib3.disable_warnings()

port = serial.Serial('/dev/ttyAMA0', baudrate=9600, timeout=2.0)

def read_pm_line(_port):
    rv = b''
    while True:
        ch1 = _port.read()
        if ch1 == b'\x42':
            ch2 = _port.read()
            if ch2 == b'\x4d':
                rv += ch1 + ch2
                rv += _port.read(28)
                return rv


count = 0
rcv_list = []
while (count < 9 ):
    try:
        rcv = read_pm_line(port)
        res = {'timestamp': datetime.datetime.now(),
               'apm10': rcv[4] * 256 + rcv[5],
               'apm25': rcv[6] * 256 + rcv[7],
               'apm100': rcv[8] * 256 + rcv[9],
               'pm10': rcv[10] * 256 + rcv[11],
               'pm25': rcv[12] * 256 + rcv[13],
               'pm100': rcv[14] * 256 + rcv[15],
               'gt03um': rcv[16] * 256 + rcv[17],
               'gt05um': rcv[18] * 256 + rcv[19],
               'gt10um': rcv[20] * 256 + rcv[21],
               'gt25um': rcv[22] * 256 + rcv[23],
               'gt50um': rcv[24] * 256 + rcv[25],
               'gt100um': rcv[26] * 256 + rcv[27]
               }
        print('===============\n'
              'PM1.0(CF=1): {}\n'
              'PM2.5(CF=1): {}\n'
              'PM10 (CF=1): {}\n'
              'PM1.0 (STD): {}\n'
              'PM2.5 (STD): {}\n'
              'PM10  (STD): {}\n'
              '>0.3um     : {}\n'
              '>0.5um     : {}\n'
              '>1.0um     : {}\n'
              '>2.5um     : {}\n'
              '>5.0um     : {}\n'
              '>10um      : {}'.format(res['apm10'], res['apm25'], res['apm100'],
                                       res['pm10'], res['pm25'], res['pm100'],
                                       res['gt03um'], res['gt05um'], res['gt10um'],
                                       res['gt25um'], res['gt50um'], res['gt100um']))
        rcv_list.append(res.copy())
        json_body_public = [
            {
                "measurement": "ppm1",
                "tags": {
                    "lat": lat,
                    "long": long,
                    "sensor_model": pms_sensor_model
                },
                "fields": {
                    "value": float(res['pm10'])
                }
            },
            {
                "measurement": "ppm25",
                "tags": {
                    "lat": lat,
                    "long": long,
                    "sensor_model": pms_sensor_model
                },
                "fields": {
                    "value": float(res['pm25'])
                }
            },
            {
                "measurement": "ppm10",
                "tags": {
                    "lat": lat,
                    "long": long,
                    "sensor_model": pms_sensor_model
                },
                "fields": {
                    "value": float(res['pm100'])
                }
            }
        ]

        client = InfluxDBClient(host='db.airmonitor.pl', port=(base64.b64decode("ODA4Ng==")),
                                username=(base64.b64decode("YWlybW9uaXRvcl9wdWJsaWNfd3JpdGU=")), password=(
            base64.b64decode("amZzZGUwMjh1cGpsZmE5bzh3eWgyMzk4eTA5dUFTREZERkdBR0dERkdFMjM0MWVhYWRm")),
                                database=(base64.b64decode("YWlybW9uaXRvcg==")), ssl=True, verify_ssl=False, timeout=10)
        client.write_points(json_body_public)
        print('Logged to database. {} documents totally.'.format(len(rcv_list)))
        count += 1
        time.sleep(5)
    except KeyboardInterrupt:
        break
