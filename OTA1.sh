#!/usr/bin/env bash
apt-mark hold raspberrypi-kernel
apt-get update
apt-get upgrade -y
