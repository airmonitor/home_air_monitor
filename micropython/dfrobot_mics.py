import utime as time

from i2c import I2CAdapter

######################################
# Constants

_MICS_ADDRESS_0 = 0x75

_MICS_ERROR = "error"

_MICS_OX_REGISTER_HIGH = 0x04
_MICS_POWER_REGISTER_MODE = 0x0A

_MICS_SLEEP_MODE = 0x00
_MICS_WAKEUP_MODE = 0x01

_MICS_CO_THRESHOLD = 0.425
_MICS_CO_FACTOR = 0.000405


class Mics(object):
    __r0_ox = 1.0
    __r0_red = 1.0

    def __init__(self, i2c: I2CAdapter):
        self.i2c = i2c
        self.addr = _MICS_ADDRESS_0

    def sleep_mode(self):
        """
        Functionality:
            Puts the MICS sensor into sleep mode by writing the _MICS_SLEEP_MODE value to the _MICS_POWER_REGISTER_MODE register.
            This method sends the sleep mode command to the sensor via I2C communication.
        """
        _data = [_MICS_SLEEP_MODE]
        self.i2c.write_i2c_block_data(
            self.addr, _MICS_POWER_REGISTER_MODE, bytes(_data)
        )

    def wakeup_mode(self):
        """
        Functionality:
            Puts the MICS sensor into wakeup mode by writing the _MICS_WAKEUP_MODE value to the _MICS_POWER_REGISTER_MODE register.
            This method sends the wakeup mode command to the sensor via I2C communication.
        """
        _data = [_MICS_WAKEUP_MODE]
        self.i2c.write_i2c_block_data(
            self.addr, _MICS_POWER_REGISTER_MODE, bytes(_data)
        )

    def get_power_mode(self):
        """
        Functionality:
            Retrieves the power mode of the MICS sensor by reading 1 byte from the I2C bus at the _MICS_POWER_REGISTER_MODE register.
            The power mode value is returned as an integer.

        Returns:
            int: The power mode value of the MICS sensor
        """
        result = self.i2c.read_i2c_block_data(self.addr, _MICS_POWER_REGISTER_MODE, 1)
        return result[0]

    def get_mics_data(self):
        """
        Functionality:
            Retrieves MICS sensor data by reading 6 bytes from the I2C bus starting from the _MICS_OX_REGISTER_HIGH register.
            The sensor data is stored in a list, where:
            - sensor_data[0] and sensor_data[1] represent the ox_data (high and low bytes)
            - sensor_data[2] and sensor_data[3] represent the red_data (high and low bytes)
            - sensor_data[4] and sensor_data[5] represent the power_data (high and low bytes)

            The method calculates the actual ox_data, red_data, and power_data by combining the high and low bytes.
            It then updates sensor_data[0] with the difference between power_data and ox_data, if the difference is positive, otherwise sets it to 0.
            Similarly, it updates sensor_data[1] with the difference between power_data and red_data, if the difference is non-negative, otherwise sets it to 0.
            Finally, it updates sensor_data[2] with the power_data.

        Returns:
            list: A list containing the updated sensor data, where:
            - sensor_data[0] represents the adjusted ox_data
            - sensor_data[1] represents the adjusted red_data
            - sensor_data[2] represents the power_data
        """
        sensor_data = list(
            self.i2c.read_i2c_block_data(self.addr, _MICS_OX_REGISTER_HIGH, 6)
        )
        ox_data = sensor_data[0] * 256 + sensor_data[1]
        red_data = sensor_data[2] * 256 + sensor_data[3]
        power_data = sensor_data[4] * 256 + sensor_data[5]
        if (power_data - ox_data) <= 0:
            sensor_data[0] = 0
        else:
            sensor_data[0] = power_data - ox_data
        if (power_data - red_data) < 0:
            sensor_data[1] = 0
        else:
            sensor_data[1] = power_data - red_data
        sensor_data[2] = power_data
        return sensor_data

    def get_gas_ppm(self, gas_type: str):
        """
        Parameters:
            gas_type (str): The type of gas to get the concentration for

        Functionality:
            Retrieves the concentration of the specified gas type in parts per million (ppm).
            Calls the `get_mics_data` method to get the sensor data.
            Calculates the ratios of rs/r0 for the red and ox values.
            Uses a dictionary `gas_getters` to map gas types to their corresponding getter methods.
            If the specified `gas_type` exists in the `gas_getters` dictionary, it calls the corresponding getter method and returns the result.
            If the `gas_type` is not found in the `gas_getters` dictionary, it returns `_MICS_ERROR`.

        Returns:
            float or str: The concentration of the specified gas type in parts per million (ppm) if the gas type is supported, or `_MICS_ERROR` if the gas type is not supported.
        """
        result = self.get_mics_data()

        rs_r0_red_data = result[1] / self.__r0_red
        rs_ro_ox_data = result[0] / self.__r0_ox

        gas_getters = {
            "CO": self.get_carbon_monoxide(rs_r0_red_data),
            "CH4": self.get_methane(rs_r0_red_data),
            "C2H5OH": self.get_ethanol(rs_r0_red_data),
            "H2": self.get_hydrogen(rs_r0_red_data),
            "NH3": self.get_ammonia(rs_r0_red_data),
            "NO2": self.get_nitrogen_dioxide(rs_ro_ox_data),
        }
        if gas_type in gas_getters.keys():
            return gas_getters.get(gas_type)
        
        return _MICS_ERROR

    def warm_up_time(self):
        """
        Functionality:
            Performs a warm-up routine for the MICS sensor.
            The warm-up routine consists of the following steps:
            1. Wait for a calibration time of 180 seconds.
            2. Retrieve the MICS sensor data using the `get_mics_data` method.
            3. Iterates 10 times:
            - Accumulates the ox and red values from the sensor data.
            - Waits for 1 second between each iteration.
            4. Calculates the average ox and red values by dividing the accumulated values by 10.
            5. Stores the average ox and red values in the `__r0_ox` and `__r0_red` instance variables, respectively.
        """
        calibration_time = 180
        for _ in range(calibration_time):
            time.sleep(1)

        for _ in range(10):
            result = self.get_mics_data()
            self.__r0_ox += result[0]
            self.__r0_red += result[1]
            time.sleep(1)

        self.__r0_ox //= 10
        self.__r0_red //= 10

    def get_gas_exist(self, gas_type):
        """
        Parameters:
            gas_type (str): The type of gas to check for existence

        Functionality:
            Retrieves MICS sensor data using the `get_mics_data` method.
            Calculates the ratios of rs/r0 for the red and ox values.
            Checks for the existence of the specified gas type using the corresponding exist_* method based on the gas_type.
            Returns the result of the exist_* method if the gas_type is found in the gas_getters dictionary.
            If the gas_type is not found, returns _MICS_ERROR.

        Returns:
            int or None: Returns 1 if the specified gas exists, None if it doesn't exist, or _MICS_ERROR if the gas_type is not supported.
        """
        result = self.get_mics_data()

        rs_r0_red_ratio = result[1] / self.__r0_red
        rs_ro_ox_ratio = result[0] / self.__r0_ox

        gas_getters = {
            "CO": self.exist_carbon_monoxide(rs_r0_red_ratio),
            "CH4": self.exist_methane(rs_r0_red_ratio),
            "C2H5OH": self.exist_ethanol(rs_r0_red_ratio),
            "C3H8": self.exist_propane(rs_r0_red_ratio),
            "C4H10": self.exist_iso_butane(rs_r0_red_ratio),
            "H2": self.exist_hydrogen(rs_r0_red_ratio),
            "H2S": self.exist_hydrogen_sulfide(rs_r0_red_ratio),
            "NH3": self.exist_ammonia(rs_r0_red_ratio),
            "NO": self.exist_nitric_oxide(rs_ro_ox_ratio),
            "NO2": self.exist_nitrogen_dioxide(rs_ro_ox_ratio),
        }

        if gas_type in gas_getters.keys():
            return gas_getters.get(gas_type)

        return _MICS_ERROR

    @staticmethod
    def get_carbon_monoxide(sensor_value):
        """
        Parameters:
            sensor_value (float): The sensor value for carbon monoxide

        Functionality:
            Calculates the carbon monoxide (CO) concentration in parts per million (ppm) based on the sensor value.
            If the sensor value is above the CO_THRESHOLD, it returns 0.0 ppm.
            If the calculated CO concentration is above 1000.0 ppm, it returns 1000.0 ppm.
            If the calculated CO concentration is below 1.0 ppm, it returns 0.0 ppm.

        Returns:
            float: The carbon monoxide concentration in parts per million (ppm)
        """
        if sensor_value > _MICS_CO_THRESHOLD:
            return 0.0
        co = (_MICS_CO_THRESHOLD - sensor_value) / _MICS_CO_FACTOR
        if co > 1000.0:
            return 1000.0
        if co < 1.0:
            return 0.0
        return co

    @staticmethod
    def get_methane(data):
        """
        Parameters:
            data (float): The sensor value for methane

        Functionality:
            Calculates the methane (CH4) concentration in parts per million (ppm) based on the sensor value.
            If the sensor value is above 0.786, it returns 0.0 ppm.
            If the calculated methane concentration is above 25000.0 ppm, it returns 25000.0 ppm.
            If the calculated methane concentration is below 1000.0 ppm, it returns 0.0 ppm.

        Returns:
            float: The methane concentration in parts per million (ppm)
        """
        if data > 0.786:
            return 0.0
        methane = (0.786 - data) / 0.000023
        if methane > 25000.0:
            return 25000.0
        if methane < 1000.0:
            return 0.0
        return methane

    @staticmethod
    def get_ethanol(data):
        """
        Parameters:
            data (float): The sensor value for ethanol

        Functionality:
            Calculates the ethanol (C2H5OH) concentration in parts per million (ppm) based on the sensor value.
            If the sensor value is above 0.306, it returns 0.0 ppm.
            If the calculated ethanol concentration is above 500.0 ppm, it returns 500.0 ppm.
            If the calculated ethanol concentration is below 10.0 ppm, it returns 0.0 ppm.

        Returns:
            float: The ethanol concentration in parts per million (ppm)
        """
        if data > 0.306:
            return 0.0
        ethanol = (0.306 - data) / 0.00057
        if ethanol > 500.0:
            return 500.0
        if ethanol < 10.0:
            return 0.0
        return ethanol

    @staticmethod
    def get_hydrogen(data):
        """
        Parameters:
            data (float): The sensor value for hydrogen

        Functionality:
            Calculates the hydrogen (H2) concentration in parts per million (ppm) based on the sensor value.
            If the sensor value is above 0.279, it returns 0.0 ppm.
            If the calculated hydrogen concentration is above 1000.0 ppm, it returns 1000.0 ppm.
            If the calculated hydrogen concentration is below 1.0 ppm, it returns 0.0 ppm.

        Returns:
            float: The hydrogen concentration in parts per million (ppm)
        """
        if data > 0.279:
            return 0.0
        hydrogen = (0.279 - data) / 0.00026
        if hydrogen > 1000.0:
            return 1000.0
        if hydrogen < 1.0:
            return 0.0
        return hydrogen

    @staticmethod
    def get_ammonia(data):
        """
        Parameters:
            data (float): The sensor value for ammonia

        Functionality:
            Calculates the ammonia (NH3) concentration in parts per million (ppm) based on the sensor value.
            If the sensor value is above 0.8, it returns 0.0 ppm.
            If the calculated ammonia concentration is above 500.0 ppm, it returns 500.0 ppm.
            If the calculated ammonia concentration is below 10.0 ppm, it returns 0.0 ppm.

        Returns:
            float: The ammonia concentration in parts per million (ppm)
        """
        if data > 0.8:
            return 0.0
        ammonia = (0.8 - data) / 0.0015
        if ammonia > 500.0:
            return 500.0
        if ammonia < 10.0:
            return 0.0
        return ammonia

    @staticmethod
    def get_nitrogen_dioxide(data):
        """
        Parameters:
            data (float): The sensor value for nitrogen dioxide

        Functionality:
            Calculates the nitrogen dioxide (NO2) concentration in parts per million (ppm) based on the sensor value.
            If the sensor value is below 1.1, it returns 0.0 ppm.
            If the calculated nitrogen dioxide concentration is above 10.0 ppm, it returns 10.0 ppm.
            If the calculated nitrogen dioxide concentration is below 0.1 ppm, it returns 0.0 ppm.

        Returns:
            float: The nitrogen dioxide concentration in parts per million (ppm)
        """
        if data < 1.1:
            return 0.0
        nitrogen_dioxide = (data - 0.045) / 6.13
        if nitrogen_dioxide > 10.0:
            return 10.0
        if nitrogen_dioxide < 0.1:
            return 0.0
        return nitrogen_dioxide

    @staticmethod
    def exist_propane(data):
        """
        Parameters:
            data (float): The sensor value for propane

        Functionality:
            Checks if propane (C3H8) exists based on the sensor value.
            If the sensor value is above 0.18, it returns None, indicating that propane does not exist.
            Otherwise, it returns 1, indicating that propane exists.

        Returns:
            int or None: Returns 1 if propane exists, or None if propane does not exist.
        """
        if data > 0.18:
            return None
        else:
            return 1

    @staticmethod
    def exist_nitric_oxide(data):
        """
        Parameters:
            data (float): The sensor value for nitric oxide

        Functionality:
            Checks if nitric oxide (NO) exists based on the sensor value.
            If the sensor value is above 0.8, it returns None, indicating that nitric oxide does not exist.
            Otherwise, it returns 1, indicating that nitric oxide exists.

        Returns:
            int or None: Returns 1 if nitric oxide exists, or None if nitric oxide does not exist.
        """
        if data > 0.8:
            return None
        else:
            return 1

    @staticmethod
    def exist_iso_butane(data):
        """
        Parameters:
            data (float): The sensor value for iso-butane

        Functionality:
            Checks if iso-butane (C4H10) exists based on the sensor value.
            If the sensor value is above 0.65, it returns None, indicating that iso-butane does not exist.
            Otherwise, it returns 1, indicating that iso-butane exists.

        Returns:
            int or None: Returns 1 if iso-butane exists, or None if iso-butane does not exist.
        """
        if data > 0.65:
            return None
        else:
            return 1

    @staticmethod
    def exist_hydrogen_sulfide(data):
        """
        Parameters:
            data (float): The sensor value for hydrogen sulfide

        Functionality:
            Checks if hydrogen sulfide (H2S) exists based on the sensor value.
            If the sensor value is between 0.58 and 0.69 (exclusive) or below 0.201, it returns 1, indicating that hydrogen sulfide exists.
            Otherwise, it returns None, indicating that hydrogen sulfide does not exist.

        Returns:
            int or None: Returns 1 if hydrogen sulfide exists, or None if hydrogen sulfide does not exist.
        """
        if data > 0.58 and data < 0.69:
            return 1
        if data < 0.201:
            return 1
        return None

    @staticmethod
    def exist_carbon_monoxide(data):
        """
        Parameters:
            data (float): The sensor value for carbon monoxide

        Functionality:
            Checks if carbon monoxide (CO) exists based on the sensor value.
            If the sensor value is above 0.425, it returns None, indicating that carbon monoxide does not exist.
            Otherwise, it returns 1, indicating that carbon monoxide exists.

        Returns:
            int or None: Returns 1 if carbon monoxide exists, or None if carbon monoxide does not exist.
        """
        if data > 0.425:
            return None
        else:
            return 1

    @staticmethod
    def exist_methane(data):
        """
        Parameters:
            data (float): The sensor value for methane

        Functionality:
            Checks if methane (CH4) exists based on the sensor value.
            If the sensor value is above 0.786, it returns None, indicating that methane does not exist.
            Otherwise, it returns 1, indicating that methane exists.

        Returns:
            int or None: Returns 1 if methane exists, or None if methane does not exist.
        """
        if data > 0.786:
            return None
        else:
            return 1

    @staticmethod
    def exist_ethanol(data):
        """
        Parameters:
            data (float): The sensor value for ethanol

        Functionality:
            Checks if ethanol (C2H5OH) exists based on the sensor value.
            If the sensor value is above 0.306, it returns None, indicating that ethanol does not exist.
            Otherwise, it returns 1, indicating that ethanol exists.

        Returns:
            int or None: Returns 1 if ethanol exists, or None if ethanol does not exist.
        """
        if data > 0.306:
            return None
        else:
            return 1

    @staticmethod
    def exist_hydrogen(data):
        """
        Parameters:
            data (float): The sensor value for hydrogen

        Functionality:
            Checks if hydrogen (H2) exists based on the sensor value.
            If the sensor value is above 0.279, it returns None, indicating that hydrogen does not exist.
            Otherwise, it returns 1, indicating that hydrogen exists.

        Returns:
            int or None: Returns 1 if hydrogen exists, or None if hydrogen does not exist.
        """
        if data > 0.279:
            return None
        else:
            return 1

    @staticmethod
    def exist_ammonia(data):
        """
        Parameters:
            data (float): The sensor value for ammonia

        Functionality:
            Checks if ammonia (NH3) exists based on the sensor value.
            If the sensor value is above 0.8, it returns None, indicating that ammonia does not exist.
            Otherwise, it returns 1, indicating that ammonia exists.

        Returns:
            int or None: Returns 1 if ammonia exists, or None if ammonia does not exist.
        """
        if data > 0.8:
            return None
        else:
            return 1

    @staticmethod
    def exist_nitrogen_dioxide(data):
        """
        Parameters:
            data (float): The sensor value for nitrogen dioxide

        Functionality:
            Checks if nitrogen dioxide (NO2) exists based on the sensor value.
            If the sensor value is below 1.1, it returns None, indicating that nitrogen dioxide does not exist.
            Otherwise, it returns 1, indicating that nitrogen dioxide exists.

        Returns:
            int or None: Returns 1 if nitrogen dioxide exists, or None if nitrogen dioxide does not exist.
        """
        if data < 1.1:
            return None
        else:
            return 1
