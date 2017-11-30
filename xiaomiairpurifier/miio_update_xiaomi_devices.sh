#!/usr/bin/env bash

miio --discover --sync &
sleep 30
killall node &
