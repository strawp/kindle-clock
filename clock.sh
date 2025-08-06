#!/bin/sh

cd /mnt/us/clock
ifup wlan0

killall python3.9
../python3/bin/python3.9 generate.py landscape

