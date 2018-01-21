#!/usr/bin/env bash
dos2unix /boot/airmonitor.txt
lat=`awk 'NR==1{print $1}' /boot/airmonitor.txt`
long=`awk 'NR==2{print $1}' /boot/airmonitor.txt`
echo $lat
echo $long
sed  -i "/lat/s/55.0000/${lat}/g" /etc/configuration/configuration.data
sed  -i "/long/s/15.0000/${long}/g" /etc/configuration/configuration.data
