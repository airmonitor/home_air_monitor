import random
import sys
import time

import machine
import ucontextlib
import ujson
import urequests
from machine import Pin, reset, sleep

from constants import API_KEY, API_URL, LAT, LONG, PARTICLE_SENSOR, TEMP_HUM_PRESS_SENSOR, TVOC_CO2_SENSOR, \
    SOUND_LEVEL_SENSOR
from i2c import I2CAdapter
from lib import logging

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(levelname)s]:%(name)s:%(message)s"))

if TEMP_HUM_PRESS_SENSOR.upper() == "BME680":
    TEMP_HUM_PRESS_SENSOR = TEMP_HUM_PRESS_SENSOR.upper()
    import bme680
if TEMP_HUM_PRESS_SENSOR.upper() == "BME280":
    TEMP_HUM_PRESS_SENSOR = TEMP_HUM_PRESS_SENSOR.upper()
    from bme280 import BME280

if PARTICLE_SENSOR.upper() in ("SDS011", "SDS021"):
    PARTICLE_SENSOR = PARTICLE_SENSOR.upper()
    from sds011 import SDS011
if PARTICLE_SENSOR.upper() == "PMS7003":
    PARTICLE_SENSOR = PARTICLE_SENSOR.upper()
    from pms7003 import PassivePms7003
    from errors import UartError
if PARTICLE_SENSOR.upper() == "PTQS1005":
    PARTICLE_SENSOR = PARTICLE_SENSOR.upper()
    logging.info(f"Using {PARTICLE_SENSOR}")
    from errors import UartError
    from ptqs1005 import PTQS1005Sensor

if TVOC_CO2_SENSOR.upper() == "CCS811":
    TVOC_CO2_SENSOR = TVOC_CO2_SENSOR.upper()
    from ccs811 import CCS811

if SOUND_LEVEL_SENSOR.upper() == "PCB_ARTIST_SOUND_LEVEL":
    SOUND_LEVEL_SENSOR = SOUND_LEVEL_SENSOR.upper()
    from pcb_artist_sound_level import PCBArtistSoundLevel

LOOP_COUNTER = 0
RANDOM_SLEEP_VALUE = random.randint(50, 59) + 540  # seconds
logging.info(f"Sleep value is {RANDOM_SLEEP_VALUE} seconds")

HARD_RESET_VALUE = int(86400 / RANDOM_SLEEP_VALUE)  # The Board will be restarted once per 24 hours
logging.info(f"Hard reset value {HARD_RESET_VALUE}")


def sds_measurements():
    """
    Initiates measurements for particulate matter (PM) using the SDS011 sensor.

    Parameters:
        None

    Functionality:
        Wakes up the SDS011 sensor, performs measurements for PM2.5 and PM10 over a period, 
        then puts the sensor back to sleep. It attempts to read the sensor values 10 times 
        with a delay between each read to ensure accurate readings.

    Returns:
        dict: A dictionary containing the PM2.5 and PM10 values if both are non-zero.
        bool: False if an OSError occurs during the sensor read operation.
    """
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
    """
    Initiates measurements for particulate matter using the PMS7003 sensor.

    Parameters:
        None

    Functionality:
        Wakes up the PMS7003 sensor, waits for it to stabilize, then reads particulate matter measurements. 
        In case of an error (OSError, UartError, TypeError), it returns an empty dictionary. 
        It ensures the sensor is put back to sleep after the operation, even if an error occurs.

    Returns:
        dict: A dictionary containing the particulate matter measurements if successful,
        or an empty dictionary if an error occurs.
    """
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
    """
    Initiates measurements for air quality using the PTQS1005 sensor.

    Parameters:
        None

    Functionality:
        - Wakes up the PTQS1005 sensor using the specified UART port and reset pin.
        - Waits for the sensor to stabilize.
        - Gathers air quality measurements from the sensor.
        - Handles exceptions that may occur during the measurement process.
        - Ensures the sensor is put back to sleep after measurements are taken.

    Returns:
        dict: A dictionary containing the air quality measurements if successful. 
              The dictionary is empty if an exception occurs during the measurement process.
    """
    output_data = {}
    ptqs1005_sensor = PTQS1005Sensor(uart=2)
    try:
        ptqs1005_sensor.wakeup(reset_pin=23)
        time.sleep(10)
        output_data = ptqs1005_sensor.measure()
    except (OSError, UartError, TypeError):
        return output_data
    finally:
        ptqs1005_sensor.sleep(reset_pin=23)

    return output_data


def pcb_artist_sound_level_measurements(sensor: PCBArtistSoundLevel) -> int:
    """
    Measures the sound level using the PCB Artist Sound Level sensor.

    Parameters:
        sensor (PCBArtistSoundLevel): The sensor object used to measure sound levels.

    Functionality:
        Reads the sound level measurement from the PCB Artist Sound Level sensor's register.
        If an OSError occurs during the read operation, logs an error message indicating the sensor was not found.

    Returns:
        int: The sound level measurement as an integer. Returns 0 if an OSError occurs.
    """
    try:
        measurement = int.from_bytes(sensor.reg_read(), "big")
        if 35 <= measurement <= 120:
            return measurement
        else:
            return 0
    except OSError:
        logging.error("Sound level sensor not found")
    return 0


def blink():
    led = Pin(2, Pin.OUT)
    led.value(1)
    time.sleep(0.1)
    led.value(0)


def blink_api_response(message):
    """
    Controls the blinking of an LED based on the API response message.

    Parameters:
        message (dict): The response message from the API.

    Functionality:
        - Checks if the message contains an "id" key.
        - If an "id" is present, it indicates a successful metric save, and the function triggers two blinks.
        - If an "id" is not present, indicating an invalid request, it triggers five blinks.
        - Finally, it calls another function to perform a single blink, regardless of the previous condition.

    Returns:
        None
    """
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
    """
    Sends the collected sensor data to a specified API endpoint using a POST request.

    Parameters:
        data (dict): The sensor data to be sent.
        This should be a dictionary where keys are sensor names and values are their respective measurements.

    Functionality:
        - Logs the data being sent to the API.
        - Converts the `data` dictionary into a JSON string using `ujson.dumps`.
        - Makes a POST request to the API_URL with the JSON string as the body and includes the API_KEY in the headers.
        - Logs the API's response.
        - Blinks an LED (or similar indicator) to signal the API response status.
        - Handles an `IndexError` exception, which may occur during the API response handling.

    Returns:
        bool:
        True if the data was successfully sent and a response was received from the API,
        False if an `IndexError` exception was caught.
    """
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


def get_sound_level_measurements(
        i2c_adapter: machine.I2C,  # noqa
        sensor_model: str,
        time_range_in_seconds: int = 900,
        sleep_time_in_seconds: int = 1
) -> dict:
    """
    Parameters:
        i2c_adapter (machine.I2C): The I2C adapter to communicate with the sensor.
        sensor_model (str): The model of the sound level sensor.
        time_range_in_seconds (int): The duration over which sound level measurements are taken.
        sleep_time_in_seconds (int): The delay between each sound level measurement.

    Functionality:
        Collects sound level measurements over a specified period from a PCB Artist Sound Level sensor. 
        It logs the sound level in decibels at each interval and calculates the maximum sound level 
        observed during the measurement period.

    Returns:
        dict: A dictionary containing the highest sound level in decibels measured during the specified time range.
    """

    end_time = time.time() + time_range_in_seconds
    max_sound_level = 0

    if sensor_model == "PCB_ARTIST_SOUND_LEVEL":
        logging.info("PCB Artist Sound Level Measurements")
        sensor = PCBArtistSoundLevel(i2c=i2c_adapter)

        logging.info("Enabling fast mode intensity measurement")
        sensor.enable_fast_mode_intensity_measurement()
        time.sleep(1)  # initial sleep allowing firmware to settle
        pcb_artist_sound_level_measurements(sensor)
        time.sleep(1)  # initial sleep allowing firmware to settle
        pcb_artist_sound_level_measurements(sensor)
        time.sleep(1)  # initial sleep allowing firmware to settle

        while time.time() < end_time:
            sound_level = pcb_artist_sound_level_measurements(sensor)
            if sound_level:
                logging.info(f"Sound level: {sound_level} dB")
                max_sound_level = max(max_sound_level, sound_level)
            time.sleep(sleep_time_in_seconds)
        logging.info(
            f"The highest sound level in dB from the last {time_range_in_seconds} seconds was {max_sound_level}")
    return {"decibel": max_sound_level}


def get_particle_measurements(sensor_model: str) -> dict:
    """
    Retrieves particle measurements from the specified sensor model.

    Parameters:
        sensor_model (str): The model of the sensor from which to retrieve measurements.

    Functionality:
        Depending on the sensor model provided,
        this function calls one of several measurement functions specific to that sensor model.
        It processes the raw data from these functions,
        rounding the values and structuring them into a dictionary that is returned.
        The function handles three types of sensors: PMS7003, PTQS1005, and SDS011/SDS021.
        Each sensor type has a different data structure and provides different types of measurements
        (e.g., PM1.0, PM2.5, PM10, TVOC, HCHO, CO2, temperature, and humidity).

    Returns:
        A dictionary containing the processed measurements from the sensor.
        The keys in the dictionary depend on the sensor model.
        For PMS7003, it includes 'pm1', 'pm25', and 'pm10'.
        For PTQS1005, it includes 'pm1', 'pm25', 'pm10', 'tvoc', 'hcho', 'co2', 'temperature', and 'humidity'.
        For SDS011/SDS021, it includes 'pm25' and 'pm10'.
        If the sensor model does not match any of the specified models or if no data could be retrieved,
        an empty dictionary is returned.
    """
    data = {}
    if sensor_model == "PMS7003":
        particle_data = pms7003_measurements()
        if particle_data:
            data = {
                "pm1": round(particle_data["PM1_0_ATM"]),
                "pm25": round(particle_data["PM2_5_ATM"]),
                "pm10": round(particle_data["PM10_0_ATM"]),
            }
    elif sensor_model == "PTQS1005":
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
    if sensor_model in {"SDS011", "SDS021"}:
        particle_data = sds_measurements()
        with ucontextlib.suppress(TypeError):
            data = {
                "pm25": round(particle_data["pm25"]),
                "pm10": round(particle_data["pm10"]),
            }
    return data


def get_tvoc_co2(sensor_model: str):
    """
    Retrieves the Total Volatile Organic Compounds (TVOC) and Carbon Dioxide (CO2) levels from the specified sensor.

    Parameters:
        sensor_model (str): The model of the sensor to retrieve data from.

    Functionality:
        Attempts to initialize the specified sensor model with the I2C adapter and address.
        If the sensor's data is ready, it returns the eCO2 and tVOC readings.
        Handles exceptions for OSError and RuntimeError by returning False.

    Returns:
        dict: A dictionary containing the "co2" and "tvoc" levels if successful.
        bool: False if an error occurs during sensor initialization or data retrieval.
    """
    if sensor_model == "CCS811":
        try:
            sensor = CCS811(i2c=i2c_adapter, addr=90)
            if sensor.data_ready():
                return {"co2": sensor.eCO2, "tvoc": sensor.tVOC}
        except (OSError, RuntimeError):
            return False


def get_temp_humid_pressure_measurements(*, sensor_model: str, i2c_adapter: machine.I2C):
    """
    Fetches temperature, humidity, and pressure measurements from specified sensor models.

    Parameters:
        sensor_model (str): The model of the sensor from which to fetch measurements. Supported models are "BME280" and "BME680".
        i2c_adapter (machine.I2C): The I2C adapter to communicate with the sensor.

    Functionality:
        This function checks the sensor model specified and initializes the appropriate sensor using the provided I2C adapter. 
        For the BME280 sensor, it fetches temperature, humidity, and pressure readings. 
        For the BME680 sensor, it additionally fetches gas resistance along with temperature, humidity, and pressure readings. 
        It logs the readings for the BME280 sensor. In case of an error (OSError, RuntimeError), it returns False.

    Returns:
        dict: A dictionary containing the sensor readings if successful. The keys are "temperature", "humidity", "pressure", and optionally "gas_resistance" for the BME680 sensor.
        bool: False if there is an error initializing the sensor or fetching the data.
    """
    if sensor_model == "BME280":
        try:
            bme = BME280(i2c=i2c_adapter)
            if bme.values:
                logging.info(f"BME280 readings {bme.values}")
                return {
                    "temperature": bme.values["temperature"],
                    "humidity": bme.values["humidity"],
                    "pressure": bme.values["pressure"],
                }
        except (OSError, RuntimeError):
            return False

    elif sensor_model == "BME680":
        try:
            sensor = bme680.BME680(i2c_device=i2c_adapter)
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

    else:
        logging.error("Sensor model not supported")
        return False


def augment_data(measurements: dict, sensor_model: str):
    """
    Enhances the measurement dictionary with additional data including latitude, longitude, and sensor model.

    Parameters:
        measurements (dict): A dictionary containing measurement data from a sensor.
        sensor_model (str): A string representing the model of the sensor.

    Functionality:
        - Rounds the values of the measurements to the nearest integer.
        - Adds the latitude ('lat') and longitude ('long') from global constants.
        - Adds the sensor model information under the key 'sensor'.
        - Returns the augmented data dictionary.

    Returns:
        dict: The augmented dictionary containing the original measurements, location data, and sensor model.
    """
    if measurements:
        data = {k: round(v) for k, v in measurements.items()}
        data["lat"] = LAT
        data["long"] = LONG
        data["sensor"] = sensor_model
        return data


if __name__ == "__main__":
    i2c_adapter = I2CAdapter(scl=Pin(22), sda=Pin(21), freq=100000)

    while True:
        try:
            if PARTICLE_SENSOR:
                logging.info(f"Using particle sensor {PARTICLE_SENSOR}")
                values = augment_data(
                    measurements=get_particle_measurements(sensor_model=PARTICLE_SENSOR),
                    sensor_model=PARTICLE_SENSOR,
                )
                send_measurements(data=values)
                del values
                time.sleep(1)

            if TEMP_HUM_PRESS_SENSOR:
                logging.info(f"Using temp/humid/pressure sensor {TEMP_HUM_PRESS_SENSOR}")
                values = augment_data(
                    measurements=get_temp_humid_pressure_measurements(
                        sensor_model=TEMP_HUM_PRESS_SENSOR,
                        i2c_adapter=i2c_adapter,
                    ),
                    sensor_model=TEMP_HUM_PRESS_SENSOR,
                )
                send_measurements(data=values)
                del values
                time.sleep(1)

            if TVOC_CO2_SENSOR:
                logging.info(f"Using tvoc/co2 sensor {TVOC_CO2_SENSOR}")
                values = augment_data(
                    measurements=get_tvoc_co2(sensor_model=TVOC_CO2_SENSOR), sensor_model=TVOC_CO2_SENSOR
                )
                send_measurements(data=values)
                del values
                time.sleep(1)

            if SOUND_LEVEL_SENSOR:
                logging.info(f"Using sound level sensor {SOUND_LEVEL_SENSOR}")
                values = augment_data(
                    measurements=get_sound_level_measurements(
                        sensor_model=SOUND_LEVEL_SENSOR,
                        i2c_adapter=i2c_adapter,
                        time_range_in_seconds=RANDOM_SLEEP_VALUE
                    ),
                    sensor_model=SOUND_LEVEL_SENSOR,
                )
                send_measurements(data=values)
                del values
                time.sleep(1)

            LOOP_COUNTER += 1
            logging.info(f"Increasing loop_counter, actual value {LOOP_COUNTER}")
            if LOOP_COUNTER == HARD_RESET_VALUE:
                logging.info(f"Resetting device, loop counter {LOOP_COUNTER}")
                reset()
            if not SOUND_LEVEL_SENSOR:
                logging.info(f"Sleeping for {RANDOM_SLEEP_VALUE} seconds")
                sleep(RANDOM_SLEEP_VALUE * 1000)

        except Exception as error:
            logging.info(f"Caught exception {error}")
            reset()
