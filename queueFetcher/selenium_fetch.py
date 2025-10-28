#!/usr/bin/env python3
"""
selenium_fetch.py
Use Selenium to sign into the site (interactive or automated),
export cookies, then fetch the JSON and save it.
"""

import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from fetcher import Fetcher
import serial

OUT_DIR = "./outstanding_json"
BASE_STATION_ID = "A"


# Absolute path to cookies file
COOKIES_FILE = "/home/user473/Documents/project/office-hours-beacon/queueFetcher/oh_cookies.json"

os.makedirs(OUT_DIR, exist_ok=True)

# Configure the serial port and baud rate
ser = serial.Serial(
    port='/dev/serial0',  # or '/dev/ttyS0' depending on your Pi model and OS
    baudrate=9600,
    timeout=1
)

def get_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    # Path to chromedriver must be on PATH or specify executable_path
    driver = webdriver.Chrome(options=opts)
    return driver

def interactive_login_and_save_cookies(login_url):
    driver = get_driver(headless=False)  # visible so you can do 2FA
    driver.get(login_url)
    print("Please sign in interactively in the browser window. Waiting 90 seconds...")
    # You can increase wait time here if you need 2FA or manual approvals.
    time.sleep(90)
    cookies = driver.get_cookies()
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f)
    print(f"Saved {len(cookies)} cookies to {COOKIES_FILE}")
    driver.quit()



if __name__ == "__main__":

    fetcher_configs = {
        'max_course': 1,
        'course_polling_interval_seconds': 2,
        'course_thread_expiration_seconds': 10,
        'active_course_scan_interval_seconds': 5
    }

    fetcher = Fetcher(BASE_STATION_ID, COOKIES_FILE, configs=fetcher_configs)

    # Precomputed valid course IDs. This list would change if new courses are added to OH queue.
    valid_course_list = [808, 815, 816, 820, 823, 825, 826, 827, 829, 830, 833, 834, 839, 850, 856, 864, 866, 868, 869, 877, 878, 880, 881, 882, 883, 884, 887, 889, 890, 893, 894, 895, 896, 897, 898, 899, 900, 901, 902, 904, 905, 906, 907, 908, 909, 910, 911, 913, 916, 917, 918, 919]
    fetcher.valid_course_list = valid_course_list

    fetcher.start_course_thread_manager(verbose=True)

    try:
        while True:
            time.sleep(2)
            events = fetcher.get_serial_events()
            for event in events:
                print(f"Serial Event: {event}")
                ser.write((event + '\n').encode('utf-8'))

    except KeyboardInterrupt:
        print("Stopping fetcher...")
        fetcher.running = False