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

OUT_DIR = "./outstanding_json"
JSON_URL = "https://oh.eecs.umich.edu/course_queues/744/outstanding_requests.json"
COOKIES_FILE = "oh_cookies.json"

os.makedirs(OUT_DIR, exist_ok=True)

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

def fetch_json_using_cookies():
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

if __name__ == "__main__":
    # Step 1: if you don't have cookies yet, run interactive login once:
    if not os.path.exists(COOKIES_FILE):
        print("No cookies found. Starting interactive login to obtain them.")
        interactive_login_and_save_cookies("https://oh.eecs.umich.edu/")
        print("Now run this script again (or it will continue to fetch once).")

    # Step 2: fetch JSON using saved cookies
    fetch_json_using_cookies()