#!/usr/local/bin/python3.6
# --------------------------------------
#    ___  ___  _ ____
#   / _ \/ _ \(_) __/__  __ __
#  / , _/ ___/ /\ \/ _ \/ // /
# /_/|_/_/  /_/___/ .__/\_, /
#                /_/   /___/
#
#           bme280.py
#  Read data from a digital pressure sensor.
#
#  Official datasheet available from :
#  https://www.bosch-sensortec.com/bst/products/all_products/bme280
#
# Author : Matt Hawkins
# Date   : 25/07/2016
#
# http://www.raspberrypi-spy.co.uk/
#
# --------------------------------------
from configparser import ConfigParser
from ctypes import c_short
from random import randrange
from smbus2 import SMBus
import json
import requests
import time
import urllib3

parser = ConfigParser(allow_no_value=False)
parser.read('/boot/configuration.data')
sensor = (parser.get('airmonitor', 'sensor_model_temp'))
lat = (parser.get('airmonitor', 'lat'))
long = (parser.get('airmonitor', 'long'))
api_key = (parser.get('airmonitor', 'api_key'))
api_url = 'https://airmonitor.pl/prod/measurements'
urllib3.disable_warnings()

DEVICE = 0x76  # Default device I2C address

bus = SMBus(1)


def getShort(data, index):
    # return two bytes from data as a signed 16-bit value
    return c_short((data[index + 1] << 8) + data[index]).value


def getUShort(data, index):
    # return two bytes from data as an unsigned 16-bit value
    return (data[index + 1] << 8) + data[index]


def getChar(data, index):
    # return one byte from data as a signed char
    result = data[index]
    if result > 127:
        result -= 256
    return result


def getUChar(data, index):
    # return one byte from data as an unsigned char
    result = data[index] & 0xFF
    return result


def readBME280ID(addr=DEVICE):
    # Chip ID Register Address
    REG_ID = 0xD0
    (chip_id, chip_version) = bus.read_i2c_block_data(addr, REG_ID, 2)
    return chip_id, chip_version


def readBME280All(addr=DEVICE):
    # Register Addresses
    REG_DATA = 0xF7
    REG_CONTROL = 0xF4
    REG_CONTROL_HUM = 0xF2

    # Oversample setting - page 27
    OVERSAMPLE_TEMP = 2
    OVERSAMPLE_PRES = 2
    MODE = 1

    # Oversample setting for humidity register - page 26
    OVERSAMPLE_HUM = 2
    bus.write_byte_data(addr, REG_CONTROL_HUM, OVERSAMPLE_HUM)

    control = OVERSAMPLE_TEMP << 5 | OVERSAMPLE_PRES << 2 | MODE
    bus.write_byte_data(addr, REG_CONTROL, control)

    # Read blocks of calibration data from EEPROM
    # See Page 22 data sheet
    cal1 = bus.read_i2c_block_data(addr, 0x88, 24)
    cal2 = bus.read_i2c_block_data(addr, 0xA1, 1)
    cal3 = bus.read_i2c_block_data(addr, 0xE1, 7)

    # Convert byte data to word values
    dig_T1 = getUShort(cal1, 0)
    dig_T2 = getShort(cal1, 2)
    dig_T3 = getShort(cal1, 4)

    dig_P1 = getUShort(cal1, 6)
    dig_P2 = getShort(cal1, 8)
    dig_P3 = getShort(cal1, 10)
    dig_P4 = getShort(cal1, 12)
    dig_P5 = getShort(cal1, 14)
    dig_P6 = getShort(cal1, 16)
    dig_P7 = getShort(cal1, 18)
    dig_P8 = getShort(cal1, 20)
    dig_P9 = getShort(cal1, 22)

    dig_H1 = getUChar(cal2, 0)
    dig_H2 = getShort(cal3, 0)
    dig_H3 = getUChar(cal3, 2)

    dig_H4 = getChar(cal3, 3)
    dig_H4 = (dig_H4 << 24) >> 20
    dig_H4 = dig_H4 | (getChar(cal3, 4) & 0x0F)

    dig_H5 = getChar(cal3, 5)
    dig_H5 = (dig_H5 << 24) >> 20
    dig_H5 = dig_H5 | (getUChar(cal3, 4) >> 4 & 0x0F)

    dig_H6 = getChar(cal3, 6)

    # Wait in ms (Datasheet Appendix B: Measurement time and current calculation)
    wait_time = 1.25 + (2.3 * OVERSAMPLE_TEMP) + ((2.3 * OVERSAMPLE_PRES) + 0.575) + ((2.3 * OVERSAMPLE_HUM) + 0.575)
    time.sleep(wait_time / 1000)  # Wait the required time

    # Read temperature/pressure/humidity
    data = bus.read_i2c_block_data(addr, REG_DATA, 8)
    pres_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
    temp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
    hum_raw = (data[6] << 8) | data[7]

    # Refine temperature
    var1 = (((temp_raw >> 3) - (dig_T1 << 1)) * dig_T2) >> 11
    var2 = (((((temp_raw >> 4) - dig_T1) * ((temp_raw >> 4) - dig_T1)) >> 12) * dig_T3) >> 14
    t_fine = var1 + var2
    temperature = float(((t_fine * 5) + 128) >> 8)

    # Refine pressure and adjust for temperature
    var1 = t_fine / 2.0 - 64000.0
    var2 = var1 * var1 * dig_P6 / 32768.0
    var2 = var2 + var1 * dig_P5 * 2.0
    var2 = var2 / 4.0 + dig_P4 * 65536.0
    var1 = (dig_P3 * var1 * var1 / 524288.0 + dig_P2 * var1) / 524288.0
    var1 = (1.0 + var1 / 32768.0) * dig_P1
    if var1 == 0:
        pressure = 0
    else:
        pressure = 1048576.0 - pres_raw
        pressure = ((pressure - var2 / 4096.0) * 6250.0) / var1
        var1 = dig_P9 * pressure * pressure / 2147483648.0
        var2 = pressure * dig_P8 / 32768.0
        pressure = pressure + (var1 + var2 + dig_P7) / 16.0

    # Refine humidity
    humidity = t_fine - 76800.0
    humidity = (hum_raw - (dig_H4 * 64.0 + dig_H5 / 16384.0 * humidity)) * (
            dig_H2 / 65536.0 * (1.0 + dig_H6 / 67108864.0 * humidity * (1.0 + dig_H3 / 67108864.0 * humidity)))
    humidity = humidity * (1.0 - dig_H1 * humidity / 524288.0)
    if humidity > 100:
        humidity = 100
    elif humidity < 0:
        humidity = 0

    return temperature / 100.0, pressure / 100.0, humidity


def main():
    temperature_values = []
    pressure_values = []
    humidity_values = []
    temp_calibration_factor = 5
    count = 0

    while count < 9:
        (chip_id, chip_version) = readBME280ID()
        print("Chip ID     :", chip_id)
        print("Version     :", chip_version)

        temperature, pressure, humidity = readBME280All()

        print("Temperature : ", temperature - temp_calibration_factor, "C")
        print("Pressure : ", pressure, "hPa")
        print("Humidity : ", humidity, "%")

        temperature_values.append(temperature - temp_calibration_factor)
        pressure_values.append(pressure)
        humidity_values.append(humidity)

        count += 1
        time.sleep(1)

    print("\n\n"
          "List of temp values from sensor {0}".format(temperature_values))
    temp_values_avg = (sum(temperature_values) / len(temperature_values))
    print("Temp Average {0}".format(temp_values_avg))

    print("\n\n"
          "List of pressure values from sensor {0}".format(pressure_values) )
    pressure_values_avg = (sum(pressure_values) / len(pressure_values))
    print("pressure Average {0}".format(pressure_values_avg))

    print("\n\n"
          "List of humidity values from sensor {0}".format(humidity_values))
    humidity_values_avg = (sum(humidity_values) / len(humidity_values))
    print("humidity Average {0}".format(humidity_values_avg))

    data = {
        "lat": str(lat),
        "long": str(long),
        "pressure": round(pressure_values_avg),
        "temperature": round(temp_values_avg),
        "humidity": round(humidity_values_avg),
        "sensor": sensor
    }
    print("Data to be sent {0}".format(data))

    resp = requests.post(
        api_url,
        timeout=10,
        data=json.dumps(data),
        headers = {"Content-Type": "application/json", "X-Api-Key": parser.get('airmonitor', 'api_key')}
    )
    print("Response code from AirMonitor API {0}".format(resp.status_code))


if __name__ == "__main__":
    time.sleep(randrange(10, 300))
    main()
