#!/usr/bin/env python3
"""
selenium_fetch.py
Use Selenium to sign into the site (interactive or automated),
export cookies, then fetch the JSON and save it.
"""

import os
import time
import json
from fetcher import Fetcher
import serial
from send_macs import send_mac_addresses

OUT_DIR = "./outstanding_json"
BASE_STATION_ID = "A"


# Absolute path to cookies file
COOKIES_FILE = "/home/user473/Documents/project/office-hours-beacon/queueFetcher/oh_cookies.json"

os.makedirs(OUT_DIR, exist_ok=True)



if __name__ == "__main__":

    fetcher_configs = {
        'max_course': 2,
        'course_polling_interval_seconds': 2,
        'course_thread_expiration_seconds': 10,
        'active_course_scan_interval_seconds': 5
    }

    fetcher = Fetcher(BASE_STATION_ID, COOKIES_FILE, configs=fetcher_configs)

    # send MAC addresses to ESP32
    print("Sending MAC addresses to ESP32...")
    send_mac_addresses()
    
    # Configure the serial port and baud rate
    ser = serial.Serial(
        port='/dev/serial0',  # or '/dev/ttyS0' depending on your Pi model and OS
        baudrate=9600,
        timeout=1
    )

    fetcher.get_valid_courses()
    fetcher.start_course_thread_manager(verbose=True)
    
    active_beacons = {}
    try:
        while True:

            events = fetcher.get_serial_events()
            
            for event in events:
                active_beacons[event['beacon_id']] = event
                if event['queue_position'] == -1:
                    del active_beacons[event['beacon_id']]

            for beacon in active_beacons.values():
                message = f"S{beacon['beacon_id']}%{beacon['queue_position']}%{beacon['course_color']}Z"
                print(f"Sending serial message: {message}")
                ser.write(message.encode('ascii'))
                time.sleep(0.002)  # brief pause between messages
             

    except KeyboardInterrupt:
        print("Stopping fetcher...")
        fetcher.running = False