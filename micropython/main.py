import time

import connect_wifi
import ujson
import urequests
from boot import (
    API_KEY,
    API_URL,
    LAT,
    LONG,
    PARTICLE_SENSOR,
    SSID,
    TEMP_HUM_PRESS_SENSOR,
    TVOC_CO2_SENSOR,
    WIFI_PASSWORD,
)
from i2c import I2CAdapter
from machine import Pin

if TEMP_HUM_PRESS_SENSOR == "BME680":
    import bme680

elif TEMP_HUM_PRESS_SENSOR == "BME280":
    import bme280

if PARTICLE_SENSOR in ["SDS011", "SDS021"]:
    import sds011
    SDS = sds011.SDS011(uart=2)
elif PARTICLE_SENSOR == "PMS7003":
    from pms7003 import PassivePms7003

if TVOC_CO2_SENSOR == "CCS811":
    import CCS811


def sds_measurements():
    try:
        SDS.read()
        return {
            "pm25": SDS.pm25,
            "pm10": SDS.pm10
        }
    except OSError:
        return False


def pms7003_measurements():
    try:
        pms = PassivePms7003(uart=2)
        pms.wakeup()
        pms_data = pms.read()
        pms.sleep()
        return pms_data
    except OSError:
        return False


def send_measurements(data):
    if data:
        post_data = ujson.dumps(data)
        res = urequests.post(
            API_URL,
            headers={"X-Api-Key": API_KEY, "Content-Type": "application/json"},
            data=post_data,
        ).json()

        return res, post_data


def get_particle_measurements():
    data = {}
    if PARTICLE_SENSOR == "PMS7003":
        particle_data = pms7003_measurements()

        data = {
            "pm1": round(particle_data["PM1_0_ATM"]),
            "pm25": round(particle_data["PM2_5_ATM"]),
            "pm10": round(particle_data["PM10_0_ATM"]),
        }

    elif PARTICLE_SENSOR in ["SDS011", "SDS021"]:
        particle_data = sds_measurements()
        data = {
            "pm25": round(particle_data["pm25"]),
            "pm10": round(particle_data["pm10"])
        }

    return data


def get_tvoc_co2():
    if TVOC_CO2_SENSOR == "CCS811":
        try:
            sensor = CCS811.CCS811(i2c=i2c_dev, addr=90)
            if sensor.data_ready():
                return {"co2": sensor.eCO2, "tvoc": sensor.tVOC}
        except (OSError, RuntimeError):
            return False


def get_temp_humid_pressure_measurements():
    if TEMP_HUM_PRESS_SENSOR == "BME680":
        try:
            sensor = bme680.BME680(i2c_device=i2c_dev)
            sensor.set_humidity_oversample(bme680.OS_2X)
            sensor.set_pressure_oversample(bme680.OS_4X)
            sensor.set_temperature_oversample(bme680.OS_8X)
            sensor.set_filter(bme680.FILTER_SIZE_3)

            if sensor.get_sensor_data():
                return {
                    "temperature": sensor.data.temperature,
                    "humidity": sensor.data.humidity,
                    "pressure": sensor.data.pressure,
                    "gas_resistance": sensor.data.gas_resistance,
                }
        except (OSError, RuntimeError):
            return False

    elif TEMP_HUM_PRESS_SENSOR == "BME280":
        try:
            bme = bme280.BME280(i2c=i2c_dev)
            if bme.values:
                return {
                    "temperature": bme.values["temperature"],
                    "humidity": bme.values["humidity"],
                    "pressure": bme.values["pressure"],
                }
        except (OSError, RuntimeError):
            return False


def augment_data(measurements, sensor_name):
    data = {}

    if measurements:
        for k, v in measurements.items():
            data[k] = round(v)
        data["lat"] = LAT
        data["long"] = LONG
        data["sensor"] = sensor_name

        return data


def blink():
    led = Pin(2, Pin.OUT)
    led.value(1)
    time.sleep(0.1)
    led.value(0)


def blink_api_response(message):
    if message == "Metric saved":
        blink()
        time.sleep(0.1)
        blink()


if __name__ == "__main__":
    connect_wifi.connect(ssid=SSID, password=WIFI_PASSWORD)

    if TEMP_HUM_PRESS_SENSOR:
        i2c_dev = I2CAdapter(scl=Pin(022), sda=Pin(021), freq=100000)

    time.sleep(10)

    while True:
        # PARTICLE_SENSOR
        parsed_values = augment_data(
            measurements=get_particle_measurements(),
            sensor_name=PARTICLE_SENSOR,
        )
        send_particle_measurements = send_measurements(data=parsed_values)
        print(send_particle_measurements)

        if send_particle_measurements:
            blink_api_response(
                message=send_particle_measurements[0].get("status")
            )

        time.sleep(1)

        # TEMP_HUM_PRESS SENSOR
        parsed_values = augment_data(
            measurements=get_temp_humid_pressure_measurements(),
            sensor_name=TEMP_HUM_PRESS_SENSOR,
        )
        send_temp_humid_pressure_measurements = send_measurements(
            data=parsed_values
        )
        print(send_temp_humid_pressure_measurements)

        if send_temp_humid_pressure_measurements:
            blink_api_response(
                message=send_temp_humid_pressure_measurements[0].get("status")
            )

        time.sleep(1)

        # CO2 TVOC SENSOR
        parsed_values = augment_data(
            measurements=get_tvoc_co2(), sensor_name=TVOC_CO2_SENSOR
        )

        send_co2_tvoc_measurements = send_measurements(
            data=parsed_values
        )
        print(send_co2_tvoc_measurements)

        if send_co2_tvoc_measurements:
            blink_api_response(
                message=send_co2_tvoc_measurements[0].get("status")
            )

    time.sleep(1800)
