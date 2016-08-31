#!/bin/bash

sleep 10
date >> /home/pi/devel/pyfrac_logs/pyfrac_crash_times.txt
# Kill omxplayer and the script if it has not been closed properly
kill -9 $(pidof omxplayer*)
kill -9 $(pidof control*)
python /home/pi/devel/pyfrac/controlloop.py
omxplayer -o hdmi --live rtsp://192.168.1.4 --win 0,0,320,240
