#!/usr/bin/env bash
apt-mark hold raspberrypi-kernel
apt-get udate
apt-get upgrade -y
