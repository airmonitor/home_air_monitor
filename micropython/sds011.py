"""
Reading format. See http://cl.ly/ekot

0 Header   '\xaa'
1 Command  '\xc0'
2 DATA1    PM2.5 Low byte
3 DATA2    PM2.5 High byte
4 DATA3    PM10 Low byte
5 DATA4    PM10 High byte
6 DATA5    ID byte 1
7 DATA6    ID byte 2
8 Checksum Low byte of sum of DATA bytes
9 Tail     '\xab'

"""

import ustruct as struct
import sys
import machine

_SDS011_CMDS = {'SET': b'\x01',
                'GET': b'\x00',
                'QUERY': b'\x04',
                'REPORTING_MODE': b'\x02',
                'DUTYCYCLE': b'\x08',
                'SLEEPWAKE': b'\x06'}


class SDS011:
    """A driver for the SDS011 particulate matter sensor.

    :param uart: The `UART` object to use.
    """

    def __init__(self, uart):
        self.uart = machine.UART(
            uart, baudrate=9600, bits=8, parity=None, stop=1
        )
        self._pm25 = 0.0
        self._pm10 = 0.0
        self._packet_status = False
        self._packet = ()

        self.set_reporting_mode_query()

    @property
    def pm25(self):
        """Return the PM2.5 concentration, in µg/m^3."""
        return self._pm25

    @property
    def pm10(self):
        """Return the PM10 concentration, in µg/m^3."""
        return self._pm10

    @property
    def packet_status(self):
        """Returns False if the received packet is corrupted."""
        return self._packet_status

    @property
    def packet(self):
        """Return the last received packet."""
        return self._packet

    def make_command(self, cmd, mode, param):
        header = b'\xaa\xb4'
        padding = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff'
        checksum = chr((ord(cmd) + ord(mode) + ord(param) + 255 + 255) % 256)
        checksum = bytes(checksum, 'utf8')
        tail = b'\xab'

        return header + cmd + mode + param + padding + checksum + tail

    def wake(self):
        """Sends wake command to sds011 (starts its fan)."""
        cmd = self.make_command(_SDS011_CMDS['SLEEPWAKE'],
                                _SDS011_CMDS['SET'], chr(1))
        self.uart.write(cmd)

    def sleep(self):
        """Sends sleep command to sds011 (stops its fan)."""
        cmd = self.make_command(_SDS011_CMDS['SLEEPWAKE'],
                                _SDS011_CMDS['SET'], chr(0))
        self.uart.write(cmd)

    def set_reporting_mode_query(self):
        cmd = self.make_command(_SDS011_CMDS['REPORTING_MODE'],
                                _SDS011_CMDS['SET'], chr(1))
        self.uart.write(cmd)

    def query(self):
        """Query new measurement data"""
        cmd = self.make_command(_SDS011_CMDS['QUERY'], chr(0), chr(0))
        self.uart.write(cmd)

    def process_measurement(self, packet):
        try:
            *data, checksum, tail = struct.unpack('<HHBBBs', packet)
            self._pm25 = data[0] / 10.0
            self._pm10 = data[1] / 10.0
            checksum_OK = (checksum == (sum(data) % 256))
            tail_OK = tail == b'\xab'
            self._packet_status = True if (checksum_OK and tail_OK) else False
        except Exception as e:
            print('Problem decoding packet:', e)
            sys.print_exception(e)

    def read(self):
        """
        Query a new measurement, wait for response and process it.
        Waits for a response during 512 characters (0.4s at 9600bauds).
        
        Return True if a response has been received, False overwise.
        """
        # Query measurement
        self.query()

        # Read measurement
        # Drops up to 512 characters before giving up finding a measurement pkt...
        for i in range(512):
            try:
                header = self.uart.read(1)
                if header == b'\xaa':
                    command = self.uart.read(1)

                    if command == b'\xc0':
                        packet = self.uart.read(8)
                        if packet != None:
                            self.process_measurement(packet)
                            return True
            except Exception as e:
                print('Problem attempting to read:', e)
                sys.print_exception(e)

        # If we gave up finding a measurement pkt
        return False
