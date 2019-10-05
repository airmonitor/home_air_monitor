#!/usr/bin/env bash

set -e
ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa
ssh-copy-id `whoami`@localhost

sudo apt update
sudo apt install -y ansible git

sleep 5

git clone https://github.com/airmonitor/home_air_monitor.git /home/pi/home_air_monitor

/usr/bin/ansible-playbook /home/pi/home_air_monitor/ansible/roles/main.yml

sudo pip3.6 install urllib3 pyserial smbus2 idna certifi chardet requests RPi.bme280 configparser
sudo reboot
