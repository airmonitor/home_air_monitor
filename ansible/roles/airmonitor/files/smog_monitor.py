#!/usr/local/bin/python3.6
# coding: utf-8

import time
from sds011 import SDS011
from configparser import ConfigParser
import urllib3
import json
import requests


def calculate_measurement(measurements: list, pm_factor: float = 1.0) -> float:
    print(f"List of values from sensor {measurements}")

    values_avg = (sum(measurements) / len(measurements))
    print(f"PM Average {values_avg}")

    for value in measurements:
        if values_avg > value * pm_factor:
            measurements.remove(max(measurements))
            values_avg = (sum(measurements) / len(measurements))
            print("Something is not quite right, some PM2,5 value is by 50% than average from last 9 measurements\n")

        elif values_avg < value * pm_factor:
            print("OK")

    print(f"PM values {measurements}")

    return values_avg


def send_data(pm25_values_avg: float, pm10_values_avg: float) -> str:
    urllib3.disable_warnings()

    data = {
        "lat": str(parser.get('airmonitor', 'lat')),
        "long": str(parser.get('airmonitor', 'long')),
        "pm25": str(float('%.2f' % pm25_values_avg)),
        "pm10": str(float('%.2f' % pm10_values_avg)),
        "sensor": parser.get('airmonitor', 'sensor_model')
    }

    resp = requests.post(api_url, timeout=10, data=json.dumps(data), headers={"Content-Type": "application/json"})
    return resp.status_code


if __name__ == "__main__":

    # Create an instance of your sensor
    sensor = SDS011('/dev/ttyAMA0')
    api_url = 'http://api.airmonitor.pl:5000/api'

    # Now we have some details about it
    print(sensor.device_id)
    print(sensor.firmware)
    print(sensor.dutycycle)
    print(sensor.workstate)
    print(sensor.reportmode)
    # Set duty cycle to nocycle (permanent)
    sensor.reset()
    sensor.workstate = SDS011.WorkStates.Measuring
    time.sleep(30)

    parser = ConfigParser()
    parser.read('/boot/configuration.data')

    COUNT = 0
    pm25_values = []
    pm10_values = []

    while COUNT < 30:
        values = sensor.get_values()
        print("Values measured: PPM10:", values[0], "PPM2.5:", values[1])
        pm25_values.append(values[1])
        pm10_values.append(values[0])
        COUNT += 1
        time.sleep(1)

    # Calculate and send measurement
    pm25_measurement_avg = calculate_measurement(measurements=pm25_values, pm_factor=1.5)
    pm10_measurement_avg = calculate_measurement(measurements=pm10_values)
    send_data(pm25_values_avg=pm25_measurement_avg, pm10_values_avg=pm10_measurement_avg)

    # Pause SDS sensor
    sensor.workstate = SDS011.WorkStates.Sleeping
