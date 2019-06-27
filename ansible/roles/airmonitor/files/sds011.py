#!/usr/bin/python3.6
# -*- coding: utf-8 -*-
"""
Copyright 2016, Frank Heuer, Germany

This file is part of SDS011.

SDS011 is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

SDS011 is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with SDS011.  If not, see <http://www.gnu.org/licenses/>.

Diese Datei ist Teil von SDS011.

SDS011 ist Freie Software: Sie können es unter den Bedingungen
der GNU General Public License, wie von der Free Software Foundation,
Version 3 der Lizenz oder (nach Ihrer Wahl) jeder späteren
veröffentlichten Version, weiterverbreiten und/oder modifizieren.

SDS011 wird in der Hoffnung, dass es nützlich sein wird, aber
OHNE JEDE GEWÄHRLEISTUNG, bereitgestellt; sogar ohne die implizite
Gewährleistung der MARKTFÄHIGKEIT oder EIGNUNG FÜR EINEN BESTIMMTEN ZWECK.
Siehe die GNU General Public License für weitere Details.

Sie sollten eine Kopie der GNU General Public License zusammen mit SDS011
erhalten haben. Wenn nicht, siehe <http://www.gnu.org/licenses/>.
"""

"""
This module contains the SDS011 class for controlling
the sds011 particle matter sensor from Nova using the HL-340-serial TTL USB adapter
"""

# this module has been updated by Teus Hagen May 2017
# all errors introduced with this update come from teus

from enum import IntEnum
import logging
import time
import struct
import serial
import math


class SDS011(object):
    """Class representing the SD011 dust sensor and its methods.
        The device_path on Win is one of your COM ports,
        on Linux it is one of "/dev/ttyUSB..." or "/dev/ttyAMA..."
    """

    '''
    The serial communication uses encoded bytes:
    each serial telegram starts with 0xAA and ends with 0xAB.
    The telegram sent to the sensor:
    the second byte is 0xB4, the 16th and 17th byte is 0xFF.
    In the response from SDS011 the second byte is 0xC5.
    If it is a response sent automaticaly by the sensor in "Initiative" Report Mode,
    the second byte is 0xC0.
    The third byte is always the command byte.
    In response to a request command or a sensor initiated response,
    the second byte is 0xC0.
    A telegram to the sensor in Report Mode:
    ------------------------
    Setting to Initiative:
    Message  aa:b4:02:01:00:00:00:00:00:00:00:00:00:00:00:ff:ff:01:ab
    Response aa:c5:02:01:00:00:cc:0b:da:ab

    Setting to Passive:
    Message  aa:b4:02:01:01:00:00:00:00:00:00:00:00:00:00:ff:ff:02:ab
    Response aa:c5:02:01:01:00:cc:0b:db:ab

    '''
    logging.getLogger(__name__).addHandler(logging.NullHandler())

    __SerialStart = 0xAA
    __SerialEnd = 0xAB
    __SendByte = 0xB4
    __ResponseByte = 0xC5
    __ReceiveByte = 0xC0
    __ResponseLength = 10
    __CommandLength = 19
    __CommandTerminator = 0xFF

    class Command(IntEnum):
        """Enumeration of SDS011 commands"""
        ReportMode = 2,
        Request = 4,
        DeviceId = 5,
        WorkState = 6,
        Firmware = 7,
        DutyCycle = 8

    class CommandMode(IntEnum):
        """Command to get the current configuration or set it"""
        Getting = 0,
        Setting = 1

    class ReportModes(IntEnum):
        '''Report modes of the sensor:
        In passive mode one has to send a request command,
        in order to get the measurement values as a response.'''
        Initiative = 0,
        Passiv = 1

    class WorkStates(IntEnum):
        '''the Work states:
        In sleeping mode it does not send any data, the fan is turned off.
        To get data one has to wake it up'''
        Sleeping = 0,
        Measuring = 1

    class UnitsOfMeasure(IntEnum):
        '''The unit of the measured values.
        Two modes are implemented:
        The default mode is MassConcentrationEuropean returning
        values in microgram/cubic meter (mg/m³).
        The other mode is ParticleConcentrationImperial returning values in
        particles / 0.01 cubic foot (pcs/0.01cft).
        The concentration is calculated by assuming
        different mean sphere diameters of pm10 or pm2.5 particles.
        '''
        # µg / m³, the mode of the sensors firmware
        MassConcentrationEuropean = 0,
        # pcs/0.01 cft (particles / 0.01 cubic foot )
        ParticelConcentrationImperial = 1
    # Constructor

    def __init__(self, device_path, **args):
        '''
        The device_path on Win is one of your COM ports.
        On Linux one of "/dev/ttyUSB..." or "/dev/ttyAMA..."
        '''
        logging.info("Start of SDS011 constructor. The device_path: %s", device_path)
        self.__timeout = 2
        if 'timeout' in args.keys():            # serial line read timeout
            self.__timeout = int(args['timeout'])
        self.__unit_of_measure = self.UnitsOfMeasure.MassConcentrationEuropean
        if 'unit_of_measure' in args.keys():      # in mass or values in concentration
            if isinstance(args['unit_of_measure'], self.UnitsOfMeasure):
                self.__unit_of_measure = args['unit_of_measure']
            else:
                raise ValueError("unit_of_measure give is not of type SDS011.UnitOfMeasure.")
        self.__device_path = device_path
        self.device = None
        try:
            self.device = serial.Serial(device_path,
                                        baudrate=9600, stopbits=serial.STOPBITS_ONE,
                                        parity=serial.PARITY_NONE,
                                        bytesize=serial.EIGHTBITS,
                                        timeout=self.__timeout)
            if self.device.isOpen() is False:
                if not self.device.open():
                    raise IOError(
                        "Unable to open USB to SDS011 for device %s" % device_path)
        except:
            raise IOError("SDS011: unable to set serial device %s" %
                          device_path)

        # ToDo: initiate whith the values, the sensor has to be queried for
        # that
        self.__firmware = None
        self.__reportmode = None
        self.__workstate = None
        self.__dutycycle = None
        self.__device_id = None
        self.__read_timeout = 0
        self.__dutycycle_start = time.time()
        self.__read_timeout_drift_percent = 2
        # within response the __device_id will be set
        first_response = self.__response()
        if len(first_response) == 0:
            # Device might be sleeping. So wake it up
            logging.warning("SDS011: While constructing the instance "
                     "the sensor is not responding. \n"
                     "Maybe in sleeping, in passive mode, or in a "
                     "duty cycle? Will wake it up.")
            self.__send(self.Command.WorkState,
                        self.__construct_data(self.CommandMode.Setting,
                                              self.WorkStates.Measuring))
            self.__send(self.Command.DutyCycle, self.__construct_data(
                self.CommandMode.Setting, 0))
        # at this point, device is awake, shure. So store this state
        self.__workstate = self.WorkStates.Measuring
        self.__get_current_config()
        logging.info("SDS011 Sensor has firmware: %s", self.__firmware)
        logging.info("SDS011 Sensor reportmode: %s", self.__reportmode)
        logging.info("SDS011 Sensor workstate: %s", self.__workstate)
        logging.info("SDS011 Sensor dutycycle: %s, None if Zero",
                     self.__dutycycle)
        logging.info("SDS011 Sensor device ID: %s", self.device_id)
        logging.log(16, "The SDS011 constructor is successfully executed.")

    # conversion parameters come from:
    # http://ir.uiowa.edu/cgi/viewcontent.cgi?article=5915&context=etd
    def mass2particles(self, pm, value):
        """Convert pm size from µg/m3 back to concentration pcs/0.01sqf"""
        if self.__unit_of_measure == self.UnitsOfMeasure.MassConcentrationEuropean:
            return value
        elif self.__unit_of_measure == self.UnitsOfMeasure.ParticelConcentrationImperial:

            pi = 3.14159
            density = 1.65 * pow(10, 12)

            if pm == 'pm10':
                radius = 2.60
            elif pm == 'pm2.5':
                radius = 0.44
            else:
                raise RuntimeError('SDS011 Wrong Mass2Particle parameter value for pm.\n \
                                    "%s" given, "pm10" or "pm2.5" expected.' % pm)
            radius *= pow(10, -6)
            volume = (4.0 / 3.0) * pi * pow(radius, 3)
            mass = density * volume
            K = 3531.5
            concentration = value / (K * mass)
            return int(concentration + 0.5)

    # Destructor
    def __del__(self):
        # it's better to clean up
        if self.device is not None:
            self.device.close()

    # ReportMode
    @property
    def device_path(self):
        """The device path of the sensor"""
        return self.__device_path

    # ReportMode
    @property
    def reportmode(self):
        """The report mode, the sensor has at the moment"""
        return self.__reportmode

    @reportmode.setter
    def reportmode(self, value):
        '''Setter for report mode. Use self.ReportMode IntEnum'''
        if (isinstance(value, self.ReportModes) or
                value is None):
            self.__send(self.Command.ReportMode, self.__construct_data(
                self.CommandMode.Setting, value))
            self.__reportmode = value
            logging.info("SDS011 set reportmode: %s", value)
        else:
            raise TypeError("Report mode must be of type SDS011.ReportModes")

    # workstate
    @property
    def workstate(self):
        """The workstate of the sensor as a value of type self.WorkStates"""
        return self.__workstate

    @workstate.setter
    def workstate(self, value):
        if (isinstance(value, self.WorkStates) or
                value is None):
            self.__send(self.Command.WorkState, self.__construct_data(
                self.CommandMode.Setting, value))
            self.__workstate = value
            logging.info("workstate setted: %s", value)
        else:
            raise TypeError("Report Mode must be of type SDS011.WorkStates")
    # dutycycle

    @property
    def dutycycle(self):
        """The duty cycle the sensor has as a value of type int"""
        return self.__dutycycle

    @dutycycle.setter
    def dutycycle(self, value):

        if (isinstance(value, int) or
                value is None):
            if value < 0 or value > 30:
                raise ValueError(
                    "SDS011 duty cycle has to be between 0 and 30 inclusive!")
            self.__send(self.Command.DutyCycle, self.__construct_data(
                self.CommandMode.Setting, value))
            self.__dutycycle = value
            # Calculate new timeout value
            self.__read_timeout = self.__calculate_read_timeout(value)
            self.__dutycycle_start = time.time()
            logging.info("SDS011 set duty cycle timeout: %s", self.__read_timeout)
            logging.info("SDS011 set Duty cycle: %s", value)
            self.__get_current_config()
        else:
            raise TypeError("SDS011 duty cycle should be of type int")

    @property
    def device_id(self):
        """The device id as a string"""
        return "{0:02x}{1:02x}".format(self.__device_id[0], self.__device_id[1]).upper()

    @property
    def firmware(self):
        """The firmware of the device"""
        return self.__firmware

    @property
    def unit_of_measure(self):
        """The unit of measure the sensor returns the values"""
        return self.__unit_of_measure
    @property
    def timeout(self):
        return self.__timeout

    def __construct_data(self, cmdmode, cmdvalue):
        '''Construct a data byte array from cmdmode and cmdvalue.
        cmdvalue has to be self.CommandMode type and cmdvalue int.
        Returns byte arry of length 2'''
        if not isinstance(cmdmode, self.CommandMode):
            raise TypeError(
                "SDS011 cmdmode must be of type {0}", type(self.CommandMode))
        if not isinstance(cmdvalue, int):
            raise TypeError("SDS011 cmdvalue must be of type {0}", type(int))
        retval = bytearray()
        retval.append(cmdmode)
        retval.append(cmdvalue)
        logging.log(16, "SDS011 data %s for commandmode %s constructed.",
                      cmdvalue, cmdmode)
        return retval

    def __get_current_config(self):
        '''Get the sensor status at construction time of this instance:
        the current status of the sensor.'''
        # Getting the Dutycycle
        response = self.__send(self.Command.DutyCycle,
                               self.__construct_data(self.CommandMode.Getting, 0))
        if response is not None and len(response) > 0:

            dutycycle = response[1]
            self.__dutycycle = dutycycle
            self.__read_timeout = self.__calculate_read_timeout(dutycycle)
            self.__dutycycle_start = time.time()
        else:
            raise RuntimeError("SDS011 duty cycle is not detectable")
        response = None

        # Getting reportmode
        response = self.__send(self.Command.ReportMode,
                               self.__construct_data(self.CommandMode.Getting, 0))
        if response is not None and len(response) > 0:
            reportmode = self.ReportModes(response[1])
            self.__reportmode = reportmode
        else:
            raise RuntimeError("SDS011 report mode is not detectable")
        response = None

        # Getting firmware
        response = self.__send(self.Command.Firmware,
                               self.__construct_data(self.CommandMode.Getting, 0))
        if response is not None and len(response) > 0:
            self.__firmware = "{0:02d}{1:02d}{2:02d}".format(
                response[0], response[1], response[2])
        else:
            raise RuntimeError("SDS011 firmware is not detectable")
        response = None

    def __calculate_read_timeout(self, timeoutvalue):
        newtimeout = 60 * timeoutvalue + \
            self.__read_timeout_drift_percent / 100 * 60 * timeoutvalue
        logging.log(18, "SDS011 timeout calculated for %s: %s",
                     timeoutvalue, newtimeout)
        return newtimeout

    def get_values(self):
        '''Get the sensor response and return measured value of PM10 and PM25'''
        logging.log(16, "SDS011 get get_values entered")
        if self.__workstate == self.WorkStates.Sleeping:
            raise RuntimeError("The SDS011 sensor is sleeping and will not " +
                               "send any values. Will wake it up first.")
        if self.__reportmode == self.ReportModes.Passiv:
            raise RuntimeError("The SDS011 sensor is in passive report mode "
                               "and will not automaticly send values. "
                               "You need to call Request() to get values.")

        self.__dutycycle_start = time.time()
        while self.dutycycle == 0 or \
                time.time() < self.__dutycycle_start + self.__read_timeout:
            response_data = self.__response()
            if len(response_data) > 0:
                logging.info(
                "SDS011 received response from sensor %d bytes.", len(response_data))
            return self.__extract_values_from_response(response_data)
        raise IOError(
            "SDS011 No data within read timeout of %d has been received." % self.__read_timeout)

    def request(self):
        """Request measurement data as a tuple from sensor when its in ReporMode.Passiv"""
        response = self.__send(self.Command.Request, bytearray())
        retval = self.__extract_values_from_response(response)
        return retval

    def __extract_values_from_response(self, response_data):
        """Extracts the value of PM25 and PM10 from sensor response"""
        data = response_data[2:6]
        value_of_2point5micro = None
        value_of_10micro = None
        if len(data) == 4:
            value_of_2point5micro = self.mass2particles(
                'pm2.5', float(data[0] + data[1] * 256) / 10.0)
            value_of_10micro = self.mass2particles(
                'pm10', float(data[2] + data[3] * 256) / 10.0)
            logging.log(14, "SDS011 get_values successful executed.")
            if self.dutycycle != 0:
                self.__dutycycle_start = time.time()
            return (value_of_10micro, value_of_2point5micro)
        elif self.dutycycle == 0:
            raise ValueError("SDS011 data is missing")

    def __send(self, command, data):
        '''The method for sending commands to the sensor and returning the response'''
        logging.log(16, "SDS011 send() entered with command %s and data %s.",
                      command.name, data)
        # Proof the input
        if not isinstance(command, self.Command):
            raise TypeError("The command must be of type SDS011.Command")
        if not isinstance(data, bytearray):
            raise TypeError("SDS011 data must be of type byte array")
        logging.log(16, "SDS011 input parameters checked")
        # Initialise the commandarray
        bytes_to_send = bytearray()
        bytes_to_send.append(self.__SerialStart)
        bytes_to_send.append(self.__SendByte)
        bytes_to_send.append(command.value)
        # Add data and set zero to the remainder
        for i in range(0, 12):
            if i < len(data):
                bytes_to_send.append(data[i])
            else:
                bytes_to_send.append(0)
        # last two bytes before the checksum is the CommandTerminator
        bytes_to_send.append(self.__CommandTerminator)
        bytes_to_send.append(self.__CommandTerminator)
        # calculate the checksum
        checksum = self.__checksum_make(bytes_to_send)
        # append the checksum
        bytes_to_send.append(checksum % 256)
        # and append the terminator for serial sent
        bytes_to_send.append(self.__SerialEnd)

        logging.log(16, "SDS011 sending: %s", "".join("%02x:" % b for b in bytes_to_send))
        # send the command
        written_bytes = self.device.write(bytes_to_send)
        self.device.flush()
        if written_bytes != len(bytes_to_send):
            raise IOError("SDS011 Not all bytes written")
        #self.__debugprt(3,"Sended and flushed: %s" % bytes_to_send)
        if len(bytes_to_send) != 19:
            logging.info("SDS011 sent: %d bytes, expected 19.", len(bytes_to_send))
        # check the receive value
        received = self.__response(command)
        if len(received) != 10:
            logging.info("SDS011 received: %d bytes, expected 10.", len(received))
        if len(received) == 0:
            raise IOError("SDS011 sensor is not responding.")
        # when no command or command is request command,
        # second byte has to be ReceiveByte
        if ((command is None or command == self.Command.Request) and
                received[1] != self.__ReceiveByte):
            raise ValueError(
                "SDS011 expected to receive value {0:#X} on a value request.\
                Received:\"{1}\"".format(self.__ReceiveByte, received[1]))
        # check, if response is response of the command, except Command.Request
        if command is not self.Command.Request:
            if received[2] != command.value:
                raise ValueError(
                    "SDS011 respomse does not belong to the command sent afore.")
            else:
                returnvalue = received[3: -2]
        else:
            returnvalue = received
        # return just the received data. Further evaluation of data outsite
        # this  function
        logging.log(18, "Leaving send() normal and returning %s", "".join("%02x:" % b for b in received[3: -2]))
        return returnvalue

    def __response(self, command=None):
        '''Get and check the response from the sensor.
           Response can be the response of a command sent or
           just the measurement data, while sensor is in report mode Initiative'''
        # receive the response while listening serial input
        bytes_received = bytearray(1)
        one_byte = bytes(0)
        while True:
            one_byte = self.device.read(1)
            '''If no bytes are read the sensor might be in sleep mode.
            It makes no sense to raise an exception here. The raise condition
            should be checked in a context outside of this fuction.'''
            if len(one_byte) > 0:
                bytes_received[0] = ord(one_byte)
                # if this is true, serial data is coming in
                if bytes_received[0] == self.__SerialStart:
                    single_byte = self.device.read(1)
                    if (((command is not None and command != self.Command.Request)
                         and ord(single_byte) == self.__ResponseByte) or
                            ((command is None or command is self.Command.Request)
                             and ord(single_byte) == self.__ReceiveByte)):
                        bytes_received.append(ord(single_byte))
                        break
            else:
                if self.__dutycycle == 0:
                    logging.error("SDS011 A sensor response has not arrived within timeout limit. "
                             "If the sensor is in sleeping mode wake it up first!"
                             " Returning an empty byte array as response!")
                else:
                    logging.info("SDS011 no response. Expected while in dutycycle.")
                return bytearray()

        thebytes = struct.unpack('BBBBBBBB', self.device.read(8))
        bytes_received.extend(thebytes)
        if command is not None and command is not self.Command.Request:
            if bytes_received[1] is not self.__ResponseByte:
                raise IOError("SDS011 no ResponseByte found in the response.")
            if bytes_received[2] != command.value:
                raise IOError(
                    "Third byte of serial data \"{0}\" received is not the expected response \
                    to the previous command: \"{1}\"".format(bytes_received[2], command.name))
        if command is None or command is self.Command.Request:
            if bytes_received[1] is not self.__ReceiveByte:
                raise IOError("SDS011 Received byte not found on the Value Request.")
        # check checksum
        if self.__checksum_make(bytes_received[0:-2]) != bytes_received[-2]:
            raise IOError("SDS011 Checksum of received data is invalid.")
        # set device_id if device Id is None, proof it, if it's not None
        if self.__device_id is None:
            self.__device_id = bytes_received[-4:-2]
        elif self.__device_id is not None and not self.__device_id.__eq__(bytes_received[-4:-2]):
            raise ValueError("SDS011 Data received (%s) does not belong "
                             "to this device with id %s.",
                             bytes_received, bytes_received[-4:-2], self.__device_id)
        logging.log(18, "SDS011 The response() was successful")
        return bytes_received

    def reset(self):
        '''
        Sets Report mode to Initiative. Workstate to Measuring and Duty cyle to 0
        '''
        self.workstate = self.WorkStates.Measuring
        self.reportmode = self.ReportModes.Initiative
        self.dutycycle = 0
        logging.info("Sensor resetted")

    def __checksum_make(self, data):
        '''
        Generates the checksum for data to be sent or received from the sensor.
        The data has to be of type byte array and must start with 0xAA,
        followed by 0xB4 or 0xC5 or 0xC0 as second byte.
        The sequence must end before the position of the checksum.
        '''
        logging.log(14, "SDS011 building the checksum for data %s.", data)
        # Build checksum for data to send or receive
        if len(data) not in (self.__CommandLength - 2, self.__ResponseLength - 2):
            raise ValueError("SDS011 Length data has to be {0} or {1}.".format(
                self.__CommandLength - 2, self.__ResponseLength))
        if data[0] != self.__SerialStart:
            raise ValueError("SDS011 data is missing the Startbit")
        if data[1] not in (self.__SendByte, self.__ResponseByte, self.__ReceiveByte):
            raise ValueError(
                "SDS011 data is missing SendBit-, ReceiveBit- or ReceiveValue-Byte")
        if data[1] != self.__ReceiveByte and data[2] not in list(map(int, self.Command)):
            raise ValueError(
                "SDS011 The data command byte value \"{0}\" is not valid.".format(data[2]))
        #checksum = command.value + bytes_to_send[15] + bytes_to_send[16]
        checksum = 0
        for i in range(2, len(data)):
            checksum = checksum + data[i]
        checksum = checksum % 256
        logging.log(14, "SDS011 Checksum calculated is {}.".format(checksum))
        return checksum
