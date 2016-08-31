#!/bin/bash

sleep 10
date >> /home/pi/devel/pyfrac_logs/pyfrac_crash_times.txt
kill -9 $(pidof omxplayer*)
python /home/pi/devel/pyfrac/controlloop.py
omxplayer -o hdmi --live rtsp://192.168.1.4 --win 0,0,1366,768
