from machine import SoftI2C


class I2CAdapter(SoftI2C):
    """Adds some of the SMBus I2c methods to the micropython I2c class,
        for enhanced compatibility.
        Use it like you would the machine.I2C class:

        From bme680.i2c import I2CAdapter
        I2c_dev = I2CAdapter(1, pins=('G15','G10'), baudrate=100000)
        sensor = bme680.BME680(i2c_device=i2c_dev)
        """

    def read_byte_data(self, addr, register):
        """ Read a single byte from register of device at addr
            Returns a single byte """
        return self.readfrom_mem(addr, register, 1)[0]

    def read_i2c_block_data(self, addr, register, length):
        """ Read a block of length from register of device at addr
            Returns a byte object filled with whatever was read """
        return self.readfrom_mem(addr, register, length)

    def write_byte_data(self, addr, register, data):
        """ Write a single byte of data to register of device at addr
            Returns None """
        return self.writeto_mem(addr, register, bytes([data]))

    def write_i2c_block_data(self, addr, register, data):
        """ Write multiple bytes of data to register of device at addr
            Returns None """
        return self.writeto_mem(addr, register, data)
