#!/usr/bin/python3.6
#coding: utf-8

import os
from configparser import ConfigParser
parser = ConfigParser()
parser.read('/boot/configuration.data')
filter_0_IP_address=(parser.get('airpurifier', 'filter_0_IP_address'))
os.system('sudo screen -S airpurifieron -d -m bash /etc/configuration/xiaomiairpurifier/airpurifiercontrol.sh ' + filter_0_IP_address + ' on silent')