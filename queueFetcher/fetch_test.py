"""
fetch_test.py
This file is created for testing on pc only. Actual production ready script is selenium_fetch.py
"""

import os
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import requests
import threading
import serial

OUT_DIR = "./outstanding_json"
JSON_URL = "https://oh.eecs.umich.edu/course_queues/905/outstanding_requests.json"

# Absolute path to cookies file
COOKIES_FILE = "C:/Users/jacky/OneDrive - Umich/EECS 473/Project/office-hours-beacon/queueFetcher/oh_cookies.json"


# Scan all course IDs from 0 to max_id and return valid ones as a list
def scan_all(max_id=1000):
    valid_id = []
    s = requests.Session()
    s = load_cookies_into_session(s)

    for course_id in range(0, max_id + 1):
        json_url = f"https://oh.eecs.umich.edu/course_queues/{course_id}/outstanding_requests.json"
        r = s.get(json_url, timeout=20)

        if r.status_code == 200:
            print(f"Valid course ID: {course_id} status: {r.status_code}")
            valid_id.append(course_id)
        else:
            print(f"Invalid course ID: {course_id} status: {r.status_code}")
    
    return valid_id


# Continuously fetch and print JSON to console
def fetch_loop(course_id = 905, polling_interval_seconds=2, verbose=False):
    s = requests.Session()
    s = load_cookies_into_session(s)

    json_url = f"https://oh.eecs.umich.edu/course_queues/{course_id}/outstanding_requests.json"

    while True:
        r = s.get(json_url, timeout=20)
        if r.status_code != 200:
            raise RuntimeError(f"Failed to fetch JSON: {r.status_code} body: {r.text[:200]}")
        data = r.json()

        if verbose: 
            print("--------------------------------")
            print(f"Fetching course {course_id}")

        if not data:
            if verbose: print("No outstanding requests")
            ser.write(bytes([0]))  # Send '0' for no requests
            time.sleep(polling_interval_seconds)
            continue
        
        up_next = data[0]
        if up_next['location'] == "B1":
            if verbose: print("B1 detected")
            ser.write(bytes([1]))  # Send '1' for B1
        else:
            ser.write(bytes([0]))  # Send '0' for not found
        
        for request in data:
            packet = f"email: {request['requester']['email']}, location: {request['location']}\n"
            # ser.write(packet.encode('utf-8'))

            if verbose:
                print(packet)




        time.sleep(polling_interval_seconds)  # wait before next fetch

def create_fetch_threads(course_ids, polling_interval_seconds=2, verbose=False):
    import threading
    threads = []
    for course_id in course_ids:
        t = threading.Thread(target=fetch_loop, args=(course_id, polling_interval_seconds, verbose))
        t.start()
        threads.append(t)
    return threads

if __name__ == "__main__":
    # Step 1: if you don't have cookies yet, run interactive login once:
    if not os.path.exists(COOKIES_FILE):
        print("Cookie files not found. Exiting...")
        exit(1)
        # print("No cookies found. Starting interactive login to obtain them.")
        # interactive_login_and_save_cookies("https://oh.eecs.umich.edu/")
        # print("Now run this script again (or it will continue to fetch once).")

    valid_id = scan_all(1000)
    print(f"{len(valid_id)} valid course IDs found!")
    print(valid_id)