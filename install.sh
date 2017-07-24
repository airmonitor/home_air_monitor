#!/usr/bin/env bash
#

read -p "Model sensora, np SDS021, SDS011, PMS7003, którego używasz, użyj wielkich liter: " sensor_model
read -p "Szerokość geograficzna umiejscowienia sensora, np 58.0000, pamiętaj użyj kropki a nie przecinka!: " lat
read -p "Długość geograficzna umiejscowienia sensora, np 16.0000, pamiętaj użyj kropki a nie przecinka!: " long
read -p "Sprawdź dane! Jeśli pomyliłeś się przy wprowadzaniu wciśnij CTRL+C i ponownie uruchom skrypt instalujący"

echo "Wprowadziłeś następujący model sensora " $sensor_model
echo "Wprowadziłeś następującą długość geograficzną "$lat
echo "Wprowadziłeś następującą szerokość geograficzną "$long

mkdir /etc/configuration/
cd /etc/configuration/
wget https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/configuration.data
wget https://gitlab.com/frankrich/sds011_particle_sensor/raw/master/Code/sds011.py
wget https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/smog_monitor.py
chmod +x *.py

sed  -i "/sensor_model/s/SDS021/${sensor_model}/g" /etc/configuration/configuration.data
sed  -i "/lat/s/000000/${lat}/g" /etc/configuration/configuration.data
sed  -i "/long/s/000000/${long}/g" /etc/configuration/configuration.data

locale-gen en_US.UTF-8
dpkg-reconfigure tzdata
sed  -i '/XKBLAYOUT/s/gb/us/g' /etc/default/keyboard


apt-get update
sudo apt-mark hold raspberrypi-kernel
apt-get dist-upgrade -y
apt-get install nfs-common psmisc vim ssl-cert libnet-ssleay-perl libauthen-pam-perl libio-pty-perl apt-show-versions python3-serial mailutils git libusb-dev mc exfat-fuse exfat-utils python3-pip screen cmake make gcc g++ libssl-dev curl libcurl4-openssl-dev libusb-dev wiringpi build-essential cmake libboost-dev libboost-thread-dev libboost-system-dev libsqlite3-dev subversion zlib1g-dev libudev-dev mlocate bc nano libc6-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libbz2-dev libexpat1-dev liblzma-dev i2c-tools python3 python3-pip aptitude -y

pip3 install -U pip
pip3 install -U setuptools
pip3 install -U pyserial
pip3 install -U requests
pip3 install -U RPi.bme280
pip3 install -U influxdb
pip3 install -U configparser

mkdir /mnt/ramdisk_ram0
echo "tmpfs                   /mnt/ramdisk_ram0       tmpfs   nodev,nosuid,size=1M 0 0" >> /etc/fstab

echo "*/5 * * * * /etc/configuration/smog_monitor.py > /tmp/smog_monitor" >> /var/spool/cron/crontabs/root

