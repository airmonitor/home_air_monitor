# About

The Repository contains a solution for creating your own air monitoring station.

This is the location of code for project page - http://airmonitor.pl/

Automated installation is conducted using ansible.

All scripts for obtaining data from sensors and sending them are written in python 3.6

# Usage
Please read the first description on the http://airmonitor.pl to connect all necessary sensors in a proper way to raspberry pi board.
 
* Create station using description from the http://airmonitor.pl/basics/requirements 
* Install vanilla raspbian os.
* Download script install.sh to /home/pi 
```bash
wget https://raw.githubusercontent.com/airmonitor/home_air_monitor/master/install.sh
``` 
* Run script and answer to questions like lat, long, particle sensor model... etc
```bash
/bin/bash /home/pi/install.sh
```
* Wait a couple of hours to complete, yes, a couple of hours because there is a step to compile python 3.6 from scratch.
* After installation, raspberry will be rebooted, and it will start to send measurements to the http://airmonitor.pl, there will be a couple cron entries created in pi user crontab for obtaining data from sensors and sending measurements to the airmonitor API.  

___
Tested on the Raspbian Jessie Lite with Raspberry Pi 3+ and Raspberry Pi 0 W

