#!/usr/bin/env bash

cp /etc/default/keyboard /etc/default/keyboard.bk
sed  -i '/XKBLAYOUT/s/gb/us/g' /etc/default/keyboard
cp /boot/cmdline.txt /boot/cmdline.txt.bk
cp /boot/config.txt /boot/config.txt.bk

sed  -i 's/console=serial0,115200 //g' /boot/cmdline.txt
sed  -i 's/fsck.repair=yes/fsck.repair=yes fsck.mode=force/g' /boot/cmdline.txt
echo "dtparam=i2c_arm=on" >> /boot/config.txt
echo "enable_uart=1" >> /boot/config.txt
echo "dtoverlay=pi3-disable-bt" >> /boot/config.txt

read -p "Model sensora, np SDS021, SDS011, PMS7003, którego używasz, użyj wielkich liter (domyślna instalacja wykorzystuje sensor SDS021): " sensor_model
read -p "Model czujnika temperatury,wilgotności i ciśnienia, np BME280, BME180, którego używasz, użyj wielkich liter (domyślna instalacja wykorzystuje czujnik BME280): " sensor_model_temp
read -p "Szerokość geograficzna umiejscowienia sensora, np 58.0000, pamiętaj użyj kropki a nie przecinka!: " lat
read -p "Długość geograficzna umiejscowienia sensora, np 16.0000, pamiętaj użyj kropki a nie przecinka!: " long
read -p "Sprawdź dane! Jeśli pomyliłeś się przy wprowadzaniu wciśnij CTRL+C i ponownie uruchom skrypt instalujący"

echo "Wprowadziłeś następujący model sensora pyłu " $sensor_model
echo "Wprowadziłeś następujący model czujnika temperatury " $sensor_model_temp
echo "Wprowadziłeś następującą długość geograficzną "$lat
echo "Wprowadziłeś następującą szerokość geograficzną "$long

rm -fr /etc/configuration
mkdir /etc/configuration/
cd /etc/configuration/
wget https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/configuration.data
wget https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/sds011.py
wget https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/smog_monitor.py
wget https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/bme280.py
chmod +x *.py

sed  -i "/sensor_model/s/SDS021/${sensor_model}/g" /etc/configuration/configuration.data
sed  -i "/sensor_model_temp/s/BME280/${sensor_model_temp}/g" /etc/configuration/configuration.data
sed  -i "/lat/s/000000/${lat}/g" /etc/configuration/configuration.data
sed  -i "/long/s/000000/${long}/g" /etc/configuration/configuration.data

read -p "Nastąpi konfiguracja strefy czasowej oraz czasu systemowego, wybierz lokalizację Europa a następnie Warsaw"
dpkg-reconfigure tzdata


read -p "Aktualizacja systemu oraz instalacja potrzebnego oprogramowania, uzbrój się w cierpliwość. Cała procedura może zająć nawet godzinę"
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
echo "*/5 * * * * /etc/configuration/bme280.py > /tmp/bme280" >> /var/spool/cron/crontabs/root

poweroff
