# noinspection PyInterpreter
import random
import connect_wifi
import ujson
import urequests
import utime
from boot import API_KEY, API_URL, LAT, LONG, PARTICLE_SENSOR, SSID, TEMP_HUM_PRESS_SENSOR, TVOC_CO2_SENSOR, WIFI_PASSWORD
from i2c import I2CAdapter
from lib import logging
from machine import Pin, reset

logging.basicConfig()
LOG = logging.getLogger(__name__)

if TEMP_HUM_PRESS_SENSOR == "BME680":
    LOG.info("Using BME680")
    import bme680
elif TEMP_HUM_PRESS_SENSOR == "BME280":
    LOG.info("Using BME280")
    import bme280

if PARTICLE_SENSOR in ("SDS011", "SDS021"):
    LOG.info("Using SDS0*")
    import sds011
    SDS = sds011.SDS011(uart=2)
elif PARTICLE_SENSOR == "PMS7003":
    LOG.info("Using PMS7003")
    from pms7003 import PassivePms7003
    from pms7003 import UartError

if TVOC_CO2_SENSOR == "CCS811":
    LOG.info("Using CCS811")
    import CCS811

if PARTICLE_SENSOR == "PTQS1005":
    LOG.info("Using PTQS1005")
    from ptqs1005 import PTQS1005Sensor


LOOP_COUNTER = 0


def sds_measurements():
    try:
        SDS.wake()
        utime.sleep(10)
        for _ in range(10):
            SDS.read()
        if SDS.pm25 != 0 and SDS.pm10 != 0:
            return {"pm25": SDS.pm25, "pm10": SDS.pm10}
        SDS.sleep()
    except OSError:
        return False


def pms7003_measurements():
    try:
        pms = PassivePms7003(uart=2)
        pms.wakeup()
        utime.sleep(10)
        return pms.read()
    except (OSError, UartError, TypeError):
        return {}
    finally:
        try:
            pms.sleep()
        except (OSError, UartError, TypeError, NameError):
            pass


def ptqs1005_measurements() -> dict:
    try:
        ptqs1005_sensor = PTQS1005Sensor(uart=2)
        return ptqs1005_sensor.measure()
    except (OSError, UartError, TypeError):
        return {}


def blink():
    led = Pin(2, Pin.OUT)
    led.value(1)
    utime.sleep(0.1)
    led.value(0)


def blink_api_response(message):
    if message.get("status") == "Metric saved":
        LOG.info("Metric saved, blinking 2 times")
        blink()
        utime.sleep(0.1)
        blink()
    else:
        LOG.info("Invalid request body, blinking 5 times")
        blink()
        utime.sleep(0.1)
        blink()
        utime.sleep(0.1)
        blink()
        utime.sleep(0.1)
        blink()
        utime.sleep(0.1)
        blink()


def send_measurements(data):
    LOG.info("Sending data to API %s", data)
    try:
        if data:
            post_data = ujson.dumps(data)
            res = urequests.post(
                API_URL,
                headers={"X-Api-Key": API_KEY, "Content-Type": "application/json"},
                data=post_data,
            ).json()
            LOG.info("API response %s", res)
            blink_api_response(message=res)
            return True
    except IndexError:
        return False


def get_particle_measurements():
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
            }
    if PARTICLE_SENSOR in ("SDS011", "SDS021"):
        particle_data = sds_measurements()
        try:
            data = {
                "pm25": round(particle_data["pm25"]),
                "pm10": round(particle_data["pm10"]),
            }
        except TypeError:
            pass
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
                LOG.info("BME280 readings %s", bme.values)
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
        i2c_dev = I2CAdapter(scl=Pin(022), sda=Pin(021), freq=100000)
    while True:
        try:
            LOG.info("Connecting to wifi...")
            connect_wifi.connect(ssid=SSID, password=WIFI_PASSWORD)
            utime.sleep(10)
            LOG.info("Wifi connected")
            if PARTICLE_SENSOR:
                LOG.info("Using particle sensor %s", PARTICLE_SENSOR)
                values = augment_data(
                    measurements=get_particle_measurements(),
                    sensor_name=PARTICLE_SENSOR,
                )
                send_measurements(data=values)
                LOG.info("Parsed values %s", values)
                utime.sleep(1)
            if TEMP_HUM_PRESS_SENSOR:
                LOG.info("Using temp/humid/pressure sensor %s", TEMP_HUM_PRESS_SENSOR)
                values = augment_data(
                    measurements=get_temp_humid_pressure_measurements(),
                    sensor_name=TEMP_HUM_PRESS_SENSOR,
                )
                send_measurements(data=values)
                utime.sleep(1)
            if TVOC_CO2_SENSOR:
                LOG.info("Using tvoc/co2 sensor %s", TVOC_CO2_SENSOR)
                values = augment_data(
                    measurements=get_tvoc_co2(), sensor_name=TVOC_CO2_SENSOR
                )
                send_measurements(data=values)
            LOOP_COUNTER += 1
            LOG.info("Increasing loop_counter, actual value %s", LOOP_COUNTER)
            if LOOP_COUNTER == 47:
                LOG.info("Resetting device, loop counter %s", LOOP_COUNTER)
                reset()
            random_sleep_value = random.randint(50, 59) + 1740
            LOG.info("Sleeping for %s", random_sleep_value)
            utime.sleep(random_sleep_value)
        except Exception as error:
            LOG.info("Caught exception %s", error)
            reset()
