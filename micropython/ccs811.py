"""
Ams CCS811 Indoor Air Quality Sensor
Date: April 2018
License: This code is public domain
Based on CCS811 datasheet. Inspired by Adafruit and Sparkfun libraries
Tested with Adafruit CCS811 Air quality breakout. Product ID: 3566
Tested on NodeMCU and Wemos D1 Mini (ESP8266) MicroPython v1.8.7-7-gb5a1a20a3
and MicroPython v1.9.3-8-g63826ac5c in 2017-11-01; ESP module with ESP8266
"""


class CCS811(object):
    """CCS811 gas sensor. Measures eCO2 in ppm and TVOC in ppb"""

    def __init__(self, i2c=None, addr=90):
        self.i2c = i2c
        self.addr = addr  # 0x5A = 90, 0x5B = 91
        self.tVOC = 0
        self.eCO2 = 0
        self.mode = 1  # Constant power mode; measurement every second
        self.error = False

        # Check if the sensor is available at i2c bus address
        devices = i2c.scan()
        if self.addr not in devices:
            raise ValueError(
                "CCS811 not found. Please check wiring. Pull nWake to ground."
            )
        # See figure 22 in datasheet: Bootloader Register Map
        # Check HW_ID register (0x20) - correct value 0x81
        hardware_id = self.i2c.readfrom_mem(self.addr, 0x20, 1)
        if hardware_id[0] != 0x81:
            raise ValueError("Wrong Hardware ID.")
        # Check Status Register (0x00) to see if valid application present-
        status = self.i2c.readfrom_mem(self.addr, 0x00, 1)
        # See figure 12 in datasheet: Status register: Bit 4: App valid
        if not (status[0] >> 4) & 0x01:
            raise ValueError("Application not valid.")
        # Application start. Write with no data to App_Start (0xF4)
        self.i2c.writeto(self.addr, bytearray([0xF4]))
        # Set drive mode 1 - see Figure 13 in datasheet: Measure Mode Register (0x01)
        self.i2c.writeto_mem(self.addr, 0x01, bytearray([0b00011000]))

    def __string__(self):
        return "eCO2: %d ppm, TVOC: %d ppb" % (s.eCO2, s.tVOC)

    def data_ready(self):
        """Returns true if new data was downloaded. Values in .eCO2 and .tVOV"""
        status = self.i2c.readfrom_mem(self.addr, 0x00, 1)
        # bit 3 in the status register: data_ready
        if (status[0] >> 3) & 0x01:
            # datasheet Figure 14: Algorithm Register Byte Order (0x02)
            register = self.i2c.readfrom_mem(self.addr, 0x02, 4)
            co2_hb = register[0]
            co2_lb = register[1]
            tvoc_hb = register[2]
            tvoc_lb = register[3]
            self.eCO2 = (co2_hb << 8) | co2_lb
            self.tVOC = (tvoc_hb << 8) | tvoc_lb
            return True
        else:
            return False

    def get_baseline(self):
        register = self.i2c.readfrom_mem(self.addr, 0x11, 2)
        hb = register[0]
        lb = register[1]
        return hb, lb

    def put_baseline(self, hb, lb):
        register = bytearray([0x00, 0x00])
        register[0] = hb
        register[1] = lb
        self.i2c.writeto_mem(self.addr, 0x11, register)

    def put_env_data(self, humidity, temp):
        env_register = bytearray([0x00, 0x00, 0x00, 0x00])
        env_register[0] = int(humidity) << 1
        t = int(temp // 1)
        tf = temp % 1
        t_h = (t + 25) << 9
        t_l = int(tf * 512)
        t_comb = t_h | t_l
        env_register[2] = t_comb >> 8
        env_register[3] = t_comb & 0xFF
        self.i2c.writeto_mem(self.addr, 0x05, env_register)
