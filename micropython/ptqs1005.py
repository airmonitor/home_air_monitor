import logging
import time

import machine
import utime

logging.basicConfig()


class Utility:
    @staticmethod
    def make_16bit_int(high, low) -> int:
        """Combine two 8-bit integers into a 16-bit integer."""
        return int(high) << 8 | int(low)


class ResponseValidator:
    """ResponseValidator class for validating response data."""

    @staticmethod
    def is_valid_header(raw_resp: bytes):
        """Check if the response header is valid."""
        magic_header = bytes([0x42, 0x4d, 0x00, 0x26])
        return raw_resp[:4] == magic_header

    @staticmethod
    def is_valid_checksum(raw_resp: bytes):
        """Check if the response checksum is valid."""
        calculated_checksum = sum(raw_resp[:40]) & 0xFFFF
        received_checksum = Utility.make_16bit_int(raw_resp[40], raw_resp[41])
        return calculated_checksum == received_checksum


class ResponseParser:
    """ResponseParser class for parsing response data."""

    @staticmethod
    def parse(raw_response: bytes) -> dict:
        """Parse raw response bytes into a dictionary of sensor data."""
        return ResponseParser.__parse_response(raw_response)

    @staticmethod
    def __parse_response(raw_resp: bytes) -> dict:
        """Parse the raw response bytes into a dictionary of sensor data."""
        if not ResponseValidator.is_valid_header(raw_resp) or not ResponseValidator.is_valid_checksum(raw_resp):
            raise Exception("Invalid response")

        parsed_data = {}
        parsed_data["pm10"] = Utility.make_16bit_int(raw_resp[4], raw_resp[5])  # PM1
        parsed_data["pm25"] = Utility.make_16bit_int(raw_resp[6], raw_resp[7])  # PM2.5
        parsed_data["pm100"] = Utility.make_16bit_int(raw_resp[8], raw_resp[9])  # PM10
        parsed_data["pm10_atm"] = Utility.make_16bit_int(raw_resp[10], raw_resp[11])  # "PM1 (atmosphere)"
        parsed_data["pm25_atm"] = Utility.make_16bit_int(raw_resp[12], raw_resp[13])  # "PM2.5 (atmosphere)"
        parsed_data["pm100_atm"] = Utility.make_16bit_int(raw_resp[14], raw_resp[15])  # "PM10 (atmosphere)"
        parsed_data["part03"] = Utility.make_16bit_int(raw_resp[16], raw_resp[17])  # "0.3um particles"
        parsed_data["part05"] = Utility.make_16bit_int(raw_resp[18], raw_resp[19])  # "0.5um particles"
        parsed_data["part10"] = Utility.make_16bit_int(raw_resp[20], raw_resp[21])  # "1.0um particles"
        parsed_data["part25"] = Utility.make_16bit_int(raw_resp[22], raw_resp[23])  # "2.5um particles"
        parsed_data["part50"] = Utility.make_16bit_int(raw_resp[24], raw_resp[25])  # "5.0um particles"
        parsed_data["part100"] = Utility.make_16bit_int(raw_resp[26], raw_resp[27])  # "10.0um particles"
        parsed_data["tvoc"] = Utility.make_16bit_int(raw_resp[28], raw_resp[29]) / 100.0  # "TVOC"  # noqa: E501
        parsed_data["tvoc_quan"] = int(raw_resp[30])  # "TVOC quantity"
        parsed_data["hcho"] = Utility.make_16bit_int(raw_resp[31], raw_resp[32]) / 100.0  # "HCHO"  # noqa: E501
        parsed_data["hcho_quan"] = int(raw_resp[33])  # "HCHO quantity"
        parsed_data["co2"] = Utility.make_16bit_int(raw_resp[34], raw_resp[35])  # "CO2"
        parsed_data["temp"] = Utility.make_16bit_int(raw_resp[36], raw_resp[37]) / 10.0  # "Temperature"
        parsed_data["hum"] = Utility.make_16bit_int(raw_resp[38], raw_resp[39]) / 10.0  # "Humidity"  # noqa: E501

        return parsed_data


class PTQS1005Driver:
    """PTQS1005Driver class for interacting with the sensor driver."""

    def __init__(self, uart: int):
        """Initialize the sensor driver with the specified UART."""
        self.ser = machine.UART(uart, baudrate=9600, bits=8, parity=None, stop=1)
        logging.debug("Serial port initialized")

    @staticmethod
    def __make_cmd(cmd: int, data: int) -> bytes:
        """Create a command packet for communication with the sensor."""
        arr = bytearray(7)
        arr[0] = 0x42
        arr[1] = 0x4d
        arr[2] = cmd & 0xFF
        arr[3] = (data & 0xFF00) >> 8
        arr[4] = data & 0xFF
        checksum = 0
        for i in range(5):
            checksum = checksum + int(arr[i])
        arr[5] = (checksum & 0xFF00) >> 8
        arr[6] = (checksum & 0xFF)
        return bytes(arr)

    def read(self) -> bytes:
        """Read data from the sensor."""
        self.__send_command()
        return self.__read_response()

    def __send_command(self):
        """Send a command to the sensor."""
        cmd = self.__make_cmd(0xac, 0)
        self.ser.write(cmd)
        utime.sleep(1e-3)

    def standby_mode(self):
        """Enable standby mode."""
        arr = bytearray(7)
        arr[0] = 0x42
        arr[1] = 0x4d
        arr[2] = 0xf4
        arr[3] = 0x00
        arr[4] = 0x00
        arr[5] = 0x01
        arr[6] = 0x83
        self.ser.write(arr)

    def active_mode(self):
        """Enable active mode."""
        arr = bytearray(7)
        arr[0] = 0x42
        arr[1] = 0x4d
        arr[2] = 0xf4
        arr[3] = 0x00
        arr[4] = 0x00
        arr[5] = 0x01
        arr[6] = 0x84
        self.ser.write(arr)

    def __read_response(self) -> bytes:
        """Read and return the sensor response."""
        resp = self.ser.read(42)
        if len(resp) != 42:
            raise Exception("Invalid response length")
        return resp


class PTQS1005Sensor:
    """PTQS1005Sensor class for interacting with the sensor."""

    def __init__(self, uart: int):
        """Initialize the sensor with the specified UART."""
        self.driver = PTQS1005Driver(uart)

    def measure(self) -> dict:
        """Measure sensor data and return a dictionary of measurements."""
        try:
            response = self.driver.read()
        except TypeError:
            time.sleep(1)
            response = self.driver.read()
        return ResponseParser.parse(response)

    def sleep(self, reset_pin: int):
        """Put the sensor in standby mode."""
        self.driver.standby_mode()

    def wakeup(self, reset_pin: int):
        """Put the sensor in active mode."""
        self.driver.active_mode()
