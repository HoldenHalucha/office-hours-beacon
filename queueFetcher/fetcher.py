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

class Fetcher:
    def __init__(self, base_station_id: str, max_course: int, cookies_file: str, timing_config: dict):

        # timing configs
        self.course_polling_interval_seconds = timing_config['course_polling_interval_seconds'] if 'course_polling_interval_seconds' in timing_config else 1
        self.course_thread_expiration_seconds = timing_config['course_thread_expiration_seconds'] if 'course_thread_expiration_seconds' in timing_config else 3600

        # data
        self.base_station_id = base_station_id
        self.max_course = max_course
        self.cookies_file = cookies_file
        self.valid_course_list = [] 
        self.active_course_threads = {}

        # thread locks
        self.active_course_list_lock = threading.Lock()

    def load_cookies_into_session(self, session):

        if not os.path.exists(self.cookies_file):
            raise FileNotFoundError("Cookies file not found. Run interactive login first.")
        cookies = json.load(open(self.cookies_file))
        for c in cookies:
            # requests expects domain without leading dot in some versions; adapt as needed
            session.cookies.set(c['name'], c['value'], domain=c.get('domain'))
        return session

    def scan_valid_courses(self, max_id=1000, verbose=False) -> list[int]:
        self.valid_course_list = []
        s = requests.Session()
        s = self.load_cookies_into_session(s)

        for course_id in range(0, max_id + 1):
            json_url = f"https://oh.eecs.umich.edu/course_queues/{course_id}/outstanding_requests.json"
            r = s.get(json_url, timeout=20)

            if r.status_code == 200:
                if verbose: print(f"Valid course ID: {course_id} status: {r.status_code}")
                self.valid_course_list.append(course_id)
            else:
                if verbose: print(f"Invalid course ID: {course_id} status: {r.status_code}")
        
        return self.valid_course_list
    
    def scan_active_courses(self, verbose: bool = False) -> list[int]:
        active_course_list = []
        s = requests.Session()
        s = self.load_cookies_into_session(s)

        for course_id in self.valid_course_list:
            json_url = f"https://oh.eecs.umich.edu/course_queues/{course_id}/outstanding_requests.json"
            r = s.get(json_url, timeout=20)

            queue = r.json()
            if not queue: continue  # No requests for current course

            if verbose:
                print(f"----------------- scanning course {course_id}---------------") 

            for request in queue:
                location = ""
                try:
                    location = request['location']
                except KeyError:
                    continue  # Skip if 'location' key is missing

                if location == "":
                    continue  # Skip if location is empty

                if location[0] == self.base_station_id[0]:  # Compare first character
                    if verbose: print(f"Active course ID: {course_id}, location: {location}\n")
                    active_course_list.append(course_id)
                    break  # No need to check further requests for this course

        return active_course_list
    
    def fetch_loop(self, course_id, polling_interval_seconds, expiration_seconds, verbose=False):
        s = requests.Session()
        s = self.load_cookies_into_session(s)
        json_url = f"https://oh.eecs.umich.edu/course_queues/{course_id}/outstanding_requests.json"

        last_active_time = time.time()
        while time.time() - last_active_time < expiration_seconds:
            r = s.get(json_url, timeout=20)
            if r.status_code != 200:
                raise RuntimeError(f"Failed to fetch JSON: {r.status_code} body: {r.text[:200]}")
            queue = r.json()

            if verbose: 
                print("--------------------------------")
                print(f"Fetching course {course_id}")
            
            for request in queue:
                packet = f"email: {request['requester']['email']}, location: {request['location']}\n"
                # ser.write(packet.encode('utf-8'))

                if verbose:
                    print(packet)
            
            time.sleep(polling_interval_seconds)

        if verbose:
            print(f"Course {course_id} thread expired after {expiration_seconds} seconds.")
    
    def spawn_course_thread(self, course_id, expiration_seconds=3600, verbose=False):
        if verbose:
            print(f"Spawning thread for course {course_id}...")
        t = threading.Thread(target=self.fetch_loop, args=(course_id, self.course_polling_interval_seconds, expiration_seconds, verbose))
        t.start()
        self.active_course_threads[course_id] = t

    def start_course_thread_manager(self, verbose=False):

        if verbose:
            print("Starting course thread manager...")
            print("Scanning for active courses...")
        
        active_course_list = self.scan_active_courses()
        if verbose:
            print(f"Active courses found: {active_course_list}")

        # if we have reached max threads, do not spawn more threads
        if len(self.active_course_threads) < self.max_course: 
            if verbose:
                print(f"we have reached max threads: {self.max_course}, not spawning more threads")
            return

        for course_id in active_course_list:
            # If no thread exists for this active course, spawn one
            if course_id not in self.active_course_threads:
                self.spawn_course_thread(course_id, expiration_seconds=self.course_thread_expiration_seconds, verbose=verbose)
        