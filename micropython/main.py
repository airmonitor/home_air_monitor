import connect_wifi
import ujson
import urequests
import time
from machine import Pin
from boot import SSID, WIFI_PASSWORD, API_URL, API_KEY, LAT, LONG
from pms7003 import PassivePms7003


def send_measurements():
    particle_data = pms7003_measurements()

    data = {"lat": str(LAT), "long": str(LONG), "pm1": particle_data["PM1_0_ATM"],
            "pm25": particle_data["PM2_5_ATM"], "pm10": particle_data["PM10_0_ATM"], "sensor": "PMS7003"}
    post_data = ujson.dumps(data)
    res = urequests.post(API_URL, headers={
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json"}, data=post_data).json()

    return res, post_data


def pms7003_measurements():
    pms = PassivePms7003(uart=2)
    pms.wakeup()
    pms_data = pms.read()
    pms.sleep()
    return pms_data


def blink():
    led = Pin(2, Pin.OUT)
    led.value(1)
    time.sleep(0.1)
    led.value(0)


if __name__ == "__main__":
    connect_wifi.connect(ssid=SSID, password=WIFI_PASSWORD)
    time.sleep(20)
    while True:
        measurements = send_measurements()

        api_response = measurements[0].get("status")
        if api_response == "Metric saved":
            blink()
            time.sleep(0.1)
            blink()
        time.sleep(10)
