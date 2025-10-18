#!/usr/bin/env python3
"""
selenium_fetch.py
Use Selenium to sign into the site (interactive or automated),
export cookies, then fetch the JSON and save it.
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

def load_cookies_into_session(session):
    if not os.path.exists(COOKIES_FILE):
        raise FileNotFoundError("Cookies file not found. Run interactive login first.")
    cookies = json.load(open(COOKIES_FILE))
    for c in cookies:
        # requests expects domain without leading dot in some versions; adapt as needed
        session.cookies.set(c['name'], c['value'], domain=c.get('domain'))
    return session

def save_json_file_using_cookies():
    s = requests.Session()
    s = load_cookies_into_session(s)
    r = s.get(JSON_URL, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch JSON: {r.status_code} body: {r.text[:200]}")
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    fn = os.path.join(OUT_DIR, f"outstanding_{ts}.json")
    with open(fn, "wb") as f:
        f.write(r.content)
    with open(os.path.join(OUT_DIR, "latest.json"), "wb") as f:
        f.write(r.content)
    print(f"Saved {fn}")

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

    # Step 2: fetch JSON using saved cookies
    # save_json_file_using_cookies()
    courses_to_monitor = [896]  # Add course IDs as needed

    # Step 3: Start threads to continuously fetch JSON for multiple courses
    threads = []
    try:
        threads = create_fetch_threads(courses_to_monitor, polling_interval_seconds=2, verbose=True)
    
    except KeyboardInterrupt:
        print("Exiting on user request.")
        for t in threads:
            t.join()