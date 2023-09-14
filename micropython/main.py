import random
import sys
import time

import ucontextlib
import ujson
import urequests
from machine import Pin, reset
from machine import lightsleep

from constants import API_KEY, API_URL, LAT, LONG, PARTICLE_SENSOR, TEMP_HUM_PRESS_SENSOR, TVOC_CO2_SENSOR
from i2c import I2CAdapter
from lib import logging

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(levelname)s]:%(name)s:%(message)s"))

if TEMP_HUM_PRESS_SENSOR.upper() == "BME680":
    TEMP_HUM_PRESS_SENSOR = TEMP_HUM_PRESS_SENSOR.upper()
    logging.info(f"Using {TEMP_HUM_PRESS_SENSOR}")
    import bme680
if TEMP_HUM_PRESS_SENSOR.upper() == "BME280":
    TEMP_HUM_PRESS_SENSOR = TEMP_HUM_PRESS_SENSOR.upper()
    logging.info(f"Using {TEMP_HUM_PRESS_SENSOR}")
    from bme280 import BME280

if PARTICLE_SENSOR.upper() in ("SDS011", "SDS021"):
    PARTICLE_SENSOR = PARTICLE_SENSOR.upper()
    logging.info(f"Using {PARTICLE_SENSOR}")
    from sds011 import SDS011
if PARTICLE_SENSOR.upper() == "PMS7003":
    PARTICLE_SENSOR = PARTICLE_SENSOR.upper()
    logging.info(f"Using {PARTICLE_SENSOR}")
    from pms7003 import PassivePms7003
    from errors import UartError
if PARTICLE_SENSOR.upper() == "PTQS1005":
    PARTICLE_SENSOR = PARTICLE_SENSOR.upper()
    logging.info(f"Using {PARTICLE_SENSOR}")
    from ptqs1005 import PTQS1005Sensor

if TVOC_CO2_SENSOR.upper() == "CCS811":
    TVOC_CO2_SENSOR = TVOC_CO2_SENSOR.upper()
    logging.info(f"Using {TVOC_CO2_SENSOR}")
    from ccs811 import CCS811

LOOP_COUNTER = 0
RANDOM_SLEEP_VALUE = random.randint(50, 59) + 540
logging.info(f"Sleep value is {RANDOM_SLEEP_VALUE} seconds")

HARD_RESET_VALUE = int(86400 / RANDOM_SLEEP_VALUE)  # The Board will be restarted once per 24 hours
logging.info(f"Hard reset value {HARD_RESET_VALUE}")


def sds_measurements():
    sds = SDS011(uart=2)
    try:
        sds.wake()
        time.sleep(10)
        for _ in range(10):
            sds.read()
        if sds.pm25 != 0 and sds.pm10 != 0:
            return {"pm25": sds.pm25, "pm10": sds.pm10}
        sds.sleep()
    except OSError:
        return False


def pms7003_measurements():
    pms = PassivePms7003(uart=2)
    try:
        pms.wakeup()
        time.sleep(10)
        return pms.read()
    except (OSError, UartError, TypeError):
        return {}
    finally:
        with ucontextlib.suppress(OSError, UartError, TypeError, NameError):
            pms.sleep()


def ptqs1005_measurements() -> dict:
    """Initialize the sensor with the specified UART."""
    output_data = {}
    ptqs1005_sensor = PTQS1005Sensor(uart=2)
    try:
        ptqs1005_sensor.wakeup(reset_pin=23)
        time.sleep(10)
        output_data = ptqs1005_sensor.measure()
        time.sleep(3)
    except (OSError, UartError, TypeError):
        return output_data
    finally:
        ptqs1005_sensor.sleep(reset_pin=23)

    return output_data


def blink():
    led = Pin(2, Pin.OUT)
    led.value(1)
    time.sleep(0.1)
    led.value(0)


def blink_api_response(message):  # sourcery skip: extract-duplicate-method
    if message.get("id"):
        logging.info("Metric saved, blinking 2 times")
        single_blink_and_sleep()
    else:
        error_response = 5
        logging.info(f"Invalid request body, blinking {error_response} times")
        for _ in range(error_response):
            single_blink_and_sleep()
    blink()


def single_blink_and_sleep():
    blink()
    time.sleep(0.1)


def send_measurements(data):
    logging.info(f"Sending data to API {data}")
    try:
        if data:
            post_data = ujson.dumps(data)
            res = urequests.post(
                API_URL,
                headers={"X-Api-Key": API_KEY, "Content-Type": "application/json"},
                data=post_data,
            ).json()
            logging.info(f"API response {res}")
            blink_api_response(message=res)
            return True
    except IndexError:
        return False


def get_particle_measurements():  # sourcery skip: use-named-expression
    data = {}
    if PARTICLE_SENSOR == "PMS7003":
        particle_data = pms7003_measurements()
        if particle_data:
            data = {
                "pm1": round(particle_data["PM1_0_ATM"]),
                "pm25": round(particle_data["PM2_5_ATM"]),
                "pm10": round(particle_data["PM10_0_ATM"]),
            }
    if PARTICLE_SENSOR == "PTQS1005":
        particle_data = ptqs1005_measurements()
        if particle_data:
            data = {
                "pm1": round(particle_data["pm10_atm"]),
                "pm25": round(particle_data["pm25_atm"]),
                "pm10": round(particle_data["pm100_atm"]),
                "tvoc": round(particle_data["tvoc"]),
                "hcho": round(particle_data["hcho"]),
                "co2": round(particle_data["co2"]),
                "temperature": round(particle_data["temp"]),
                "humidity": round(particle_data["hum"]),
            }
    if PARTICLE_SENSOR in ("SDS011", "SDS021"):
        particle_data = sds_measurements()
        with ucontextlib.suppress(TypeError):
            data = {
                "pm25": round(particle_data["pm25"]),
                "pm10": round(particle_data["pm10"]),
            }
    return data


def get_tvoc_co2():
    if TVOC_CO2_SENSOR == "CCS811":
        try:
            sensor = CCS811(i2c=i2c_dev, addr=90)
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
            bme = BME280(i2c=i2c_dev)
            if bme.values:
                logging.info(f"BME280 readings {bme.values}")
                return {
                    "temperature": bme.values["temperature"],
                    "humidity": bme.values["humidity"],
                    "pressure": bme.values["pressure"],
                }
        except (OSError, RuntimeError):
            return False


def augment_data(measurements, sensor_name):
    if measurements:
        data = {k: round(v) for k, v in measurements.items()}
        data["lat"] = LAT
        data["long"] = LONG
        data["sensor"] = sensor_name
        return data


if __name__ == "__main__":
    if TEMP_HUM_PRESS_SENSOR:
        i2c_dev = I2CAdapter(scl=Pin(22), sda=Pin(21), freq=100000)
    while True:
        try:
            if PARTICLE_SENSOR:
                logging.info(f"Using particle sensor {PARTICLE_SENSOR}")
                values = augment_data(
                    measurements=get_particle_measurements(),
                    sensor_name=PARTICLE_SENSOR,
                )
                send_measurements(data=values)
                time.sleep(1)
            if TEMP_HUM_PRESS_SENSOR:
                logging.info(f"Using temp/humid/pressure sensor {TEMP_HUM_PRESS_SENSOR}")  # noqa: E501
                values = augment_data(
                    measurements=get_temp_humid_pressure_measurements(),
                    sensor_name=TEMP_HUM_PRESS_SENSOR,
                )
                send_measurements(data=values)
                time.sleep(1)
            if TVOC_CO2_SENSOR:
                logging.info(f"Using tvoc/co2 sensor {TVOC_CO2_SENSOR}")
                values = augment_data(
                    measurements=get_tvoc_co2(), sensor_name=TVOC_CO2_SENSOR
                )
                send_measurements(data=values)
            LOOP_COUNTER += 1
            logging.info(f"Increasing loop_counter, actual value {LOOP_COUNTER}")
            if LOOP_COUNTER == HARD_RESET_VALUE:
                logging.info(f"Resetting device, loop counter {LOOP_COUNTER}")
                reset()
            lightsleep(RANDOM_SLEEP_VALUE * 1000)
        except Exception as error:
            logging.info(f"Caught exception {error}")
            reset()
