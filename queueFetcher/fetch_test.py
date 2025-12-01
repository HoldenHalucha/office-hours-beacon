"""
fetch_test.py
This file is created for testing on pc only. Actual production ready script is selenium_fetch.py
"""

from fetcher import Fetcher
import os
import time
from functools import wraps
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json

BASE_STATION_ID = "A"

# Absolute path to cookies file
COOKIES_FILE = "C:/Users/wendy/OneDrive - Umich/EECS 473/Project/office-hours-beacon/queueFetcher/oh_cookies.json"

def timeit(func):
    """Decorator that prints the time a function takes to execute."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__} took {elapsed:.4f} seconds")
        return result
    return wrapper

fetcher_configs = {
    'max_course': 5,
    'course_polling_interval_seconds': 1,
    'course_thread_expiration_seconds': 10,
    'active_course_scan_interval_seconds': 2
}

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

def test_fetcher():
    fetcher = Fetcher(BASE_STATION_ID, COOKIES_FILE, configs=fetcher_configs)


    fetcher.get_valid_courses()
    fetcher.start_course_thread_manager(verbose=False)

    try:
        while True:
            time.sleep(2)
            events = fetcher.get_serial_events()

            for event in events:
                message = f"S{event['beacon_id']}%{event['queue_position']}%{event['course_color']}Z"
                print(message)       
            

    except:
        print("Stopping fetcher...")
        fetcher.running = False

def get_cookies():
    interactive_login_and_save_cookies("https://eecsoh.eecs.umich.edu/")

if __name__ == "__main__":
    
    # fetcher = Fetcher(BASE_STATION_ID, COOKIES_FILE, configs=fetcher_configs)
    # fetcher.get_valid_courses(verbose=True)
    # fetcher.scan_active_courses(verbose=True)

    test_fetcher()