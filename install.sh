#!/usr/bin/env bash

set -e

USER=`whoami`
ssh-keygen
ssh-copy-id ${USER}@localhost

sudo apt update
sudo apt install -y ansible git

sleep 5

git clone https://github.com/airmonitor/home_air_monitor.git /home/pi/home_air_monitor

/usr/bin/ansible-playbook /home/pi/home_air_monitor/ansible/main.yml

poweroff
