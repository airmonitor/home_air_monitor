#!/usr/bin/env bash

cd /etc/configuration/xiaomiairpurifier

if [ "$2" == "on" ]; then
/bin/node /etc/configuration/xiaomiairpurifier/airpurifier.js $1 buzzer false
/bin/node /etc/configuration/xiaomiairpurifier/airpurifier.js $1 fanmode $3
        if [ "$4" != "" ]; then
                /bin/node /etc/configuration/xiaomiairpurifier/airpurifier.js $1 fanspeed $4
        fi
/bin/node /etc/configuration/xiaomiairpurifier/airpurifier.js $1 power true
/bin/node /etc/configuration/xiaomiairpurifier/airpurifier.js $1 led off
fi

if [ "$2" == "off" ]; then
/bin/node /etc/configuration/xiaomiairpurifier/airpurifier.js $1 power false
fi
