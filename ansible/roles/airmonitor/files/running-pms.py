#!/usr/local/bin/python3.6
# coding: utf-8

import serial
import datetime
import time
from configparser import ConfigParser
import urllib3
import requests
import json

parser = ConfigParser(allow_no_value=False)
parser.read('/boot/configuration.data')
sensor_model = (parser.get('airmonitor', 'sensor_model'))
lat = (parser.get('airmonitor', 'lat'))
long = (parser.get('airmonitor', 'long'))
urllib3.disable_warnings()

PORT = serial.Serial('/dev/ttyAMA0', baudrate=9600, timeout=2.0)
API_URL = 'http://api.airmonitor.pl:5000/api'

RCV_LIST = []
PM10_VALUES = []
PM25_VALUES = []
PM100_VALUES = []


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


def get_measurements(count):
    while count < 9:
        try:
            rcv = read_pm_line(PORT)
            res = {
                'timestamp': datetime.datetime.now(),
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
            print(
                '===============\n'
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
                                         res['gt25um'], res['gt50um'], res['gt100um'])
            )

            PM10_VALUES.append(res['pm10'])
            PM25_VALUES.append(res['pm25'])
            PM100_VALUES.append(res['pm100'])

            RCV_LIST.append(res.copy())

            print(''.format(len(RCV_LIST)))
            count += 1
            time.sleep(1)
        except KeyboardInterrupt:
            break


def calculate_pm_averages(metrics_list, factor):
    pm_values_avg = (sum(metrics_list) / len(metrics_list))

    for value in metrics_list:
        if pm_values_avg > value * factor:
            metrics_list.remove(max(metrics_list))
            pm_values_avg = (sum(metrics_list) / len(metrics_list))
            print("Something is not quite right, some value is bigger by 50% than average from last 9 measurements\n")
        elif pm_values_avg < value * factor:
            print("OK")
    return pm_values_avg


def send_data(pm10_values, pm25_values, pm100_values):
    data = {
        "lat": str(lat),
        "long": str(long),
        "pm1": str(float('%.2f' % pm10_values)),
        "pm25": str(float('%.2f' % pm25_values)),
        "pm10": str(float('%.2f' % pm100_values)),
        "sensor": sensor_model
    }

    resp = requests.post(API_URL, timeout=10, data=json.dumps(data), headers={"Content-Type": "application/json"})
    print("Response code from AirMonitor API {}", resp.status_code)


def send_data_to_domoticz(domoticz_ip, domoticz_port, pm25_idx, pm25_values):
    pm25_inside = requests.get("http://{0}:{1}/json.htm?type=command&param=udevice&idx={2}&nvalue=0&svalue={3}".format(
        domoticz_ip, domoticz_port, pm25_idx, pm25_values), timeout=10)
    return pm25_inside.status_code


if __name__ == "__main__":
    factor = 1.5
    domoticz_ip_address = "192.168.1.145"
    domoticz_port = "8080"
    inside_pm25_idx = "38"
    inside_pm10_idx = "39"

    get_measurements(count=0)
    pm10_values_avg = round((calculate_pm_averages(PM10_VALUES, factor=factor)), 0)
    pm25_values_avg = round((calculate_pm_averages(PM25_VALUES, factor=factor)), 0)
    pm100_values_avg = round((calculate_pm_averages(PM100_VALUES, factor=factor)), 0)

    send_data(
        pm10_values=pm10_values_avg,
        pm25_values=pm25_values_avg,
        pm100_values=pm100_values_avg
    )

    pm25 = send_data_to_domoticz(
        domoticz_ip=domoticz_ip_address,
        domoticz_port=domoticz_port,
        pm25_idx=inside_pm25_idx,
        pm25_values=pm25_values_avg
    )
    print("Response from domoticz - PM25 - {}".format(pm25))

    pm10 = send_data_to_domoticz(
        domoticz_ip=domoticz_ip_address,
        domoticz_port=domoticz_port,
        pm25_idx=inside_pm10_idx,
        pm25_values=pm10_values_avg
    )
    print("Response from domoticz - PM10 - {}".format(pm10))
