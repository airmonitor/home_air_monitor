import machine

###############################################
# Constants

# I2C address
PCB_ARTISTS_DBM = 0x48

# Registers
_PCB_ARTISTS_I2C_REG_VERSION = 0x00
_PCB_ARTISTS_I2C_REG_ID3 = 0x01
_PCB_ARTISTS_I2C_REG_ID2 = 0x02
_PCB_ARTISTS_I2C_REG_ID1 = 0x03
_PCB_ARTISTS_I2C_REG_ID0 = 0x04
_PCB_ARTISTS_I2C_REG_SCRATCH = 0x05
_PCB_ARTISTS_I2C_REG_CONTROL = 0x06
_PCB_ARTISTS_I2C_REG_TAVG_HIGH = 0x07
_PCB_ARTISTS_I2C_REG_TAVG_LOW = 0x08
_PCB_ARTISTS_I2C_REG_RESET = 0x09
_PCB_ARTISTS_I2C_REG_DECIBEL = 0x0A
_PCB_ARTISTS_I2C_REG_MIN = 0x0B
_PCB_ARTISTS_I2C_REG_MAX = 0x0C
_PCB_ARTISTS_I2C_REG_THR_MIN = 0x0D
_PCB_ARTISTS_I2C_REG_THR_MAX = 0x0E
_PCB_ARTISTS_I2C_REG_HISTORY_0 = 0x14
_PCB_ARTISTS_I2C_REG_HISTORY_99 = 0x77

###############################################
# Settings


class PCBArtistSoundLevel:
    def __init__(self, i2c: machine.I2C, addr: int = PCB_ARTISTS_DBM):
        """
        Initializes the PCBArtistSoundLevel object.

        Args:
            i2c: The I2C object used for communication.
            addr (optional): The address of the dB sensor. Default to PCB_ARTISTS_DBM.

        Returns:
            None

        Raises:
            None
        """

        self.i2c = i2c
        self.addr = addr

    def reg_write(self, *, reg: int, data):
        """
        Write bytes to the specified register.
        """

        # Construct message
        msg = bytearray()
        msg.append(data)

        # Write out the message to register
        self.i2c.writeto_mem(self.addr, reg, msg)

    def reg_read(self, *, reg: int = _PCB_ARTISTS_I2C_REG_DECIBEL, nbytes=1):
        """
        Reads data from a register of the dB sensor.

        Args:
            reg: The register address to read from. Default to I2C_REG_DECIBEL.
            nbytes: The number of bytes to read. Default to 1.

        Returns:
            bytearray: The data read from the register.

        Raises:
            None
        """

        return bytearray() if nbytes < 1 else self.i2c.readfrom_mem(self.addr, reg, nbytes)

    def db_sensor_version(self, reg: int = _PCB_ARTISTS_I2C_REG_VERSION) -> int:
        """
        Returns the version of the dB sensor.

        Args:
            reg (optional): The register address to read from. Default to I2C_REG_VERSION.

        Returns:
            int: The version of the dB sensor.

        Raises:
            None
        """

        read_data = self.reg_read(reg=reg)
        return int.from_bytes(read_data, "big")

    def db_sensor_id(self, reg: int = _PCB_ARTISTS_I2C_REG_ID3, nbytes: int = 4) -> int:
        """
        Returns the ID of the dB sensor.

        Args:
            reg (optional): The register address to read from. Default to I2C_REG_ID3.
            nbytes (optional): The number of bytes to read. Default to 4.

        Returns:
            int: The ID of the dB sensor.

        Raises:
            None
        """

        read_data = self.reg_read(reg=reg, nbytes=nbytes)
        return int.from_bytes(read_data, "big")

    def enable_fast_mode_intensity_measurement(self):
        """
        Enables fast mode for intensity measurement.
        TavgH = 0, TavgL = 125

        Returns:
            None

        Raises:
            None
        """

        self.reg_write(reg=_PCB_ARTISTS_I2C_REG_TAVG_LOW, data=0x7D)
        self.reg_write(reg=_PCB_ARTISTS_I2C_REG_TAVG_HIGH, data=0x00)

    def enable_standard_mode_intensity_measurement(self):
        """
        Enables fast mode for intensity measurement.
        TavgH = 0x03, TavgL = 0xE8

        Args:
            None

        Returns:
            None

        Raises:
            None
        """

        self.reg_write(reg=_PCB_ARTISTS_I2C_REG_TAVG_LOW, data=0xE8)
        self.reg_write(reg=_PCB_ARTISTS_I2C_REG_TAVG_HIGH, data=0x03)
