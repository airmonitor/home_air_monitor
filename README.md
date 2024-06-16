# About

Repository contains solution for creating your own air monitoring station.

This is location of code for project page http://airmonitor.pl/

Automated installation is conducted using ansible.

All scripts for obtaining data from sensors and sending them are written in python 3.6

# Usage

Please read the first description on the http://airmonitor.pl to connect all necessary sensors in a proper way to
raspberry pi board.

1. https://airmonitor.pl/prod/necessary_components
2. https://airmonitor.pl/prod/wiring_diagram
3. https://airmonitor.pl/prod/micropython

```shell
from machine import Pin, reset, sleep
from i2c import I2CAdapter
i2c_adapter = I2CAdapter(scl=Pin(22), sda=Pin(21), freq=100000)
from dfrobot_mics import Mics
__r0_ox = 1.0
__r0_red = 1.0
dfrobot = Mics(i2c_adapter)
dfrobot.wakeup_mode()
dfrobot.get_power_mode()
dfrobot.warm_up_time()

result = dfrobot.get_mics_data()
rs_r0_red_data = float(result[1]) / float(__r0_red)
rs_ro_ox_data = float(result[0]) / float(__r0_ox)

dfrobot.get_gas_ppm("CO")
dfrobot.get_gas_ppm("CH4")
dfrobot.get_gas_ppm("C2H5OH")
dfrobot.get_gas_ppm("H2")
dfrobot.get_gas_ppm("NH3")
dfrobot.get_gas_ppm("NH3")
dfrobot.get_gas_ppm("NO2")
```