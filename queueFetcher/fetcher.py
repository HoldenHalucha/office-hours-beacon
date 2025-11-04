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
import math

class Fetcher:
    def __init__(self, base_station_id: str, cookies_file: str, configs: dict):

        self.running = False

        # timing configs
        self.max_course = configs['max_course'] if 'max_course' in configs else 5
        self.course_polling_interval_seconds = configs['course_polling_interval_seconds'] if 'course_polling_interval_seconds' in configs else 1
        self.course_thread_expiration_seconds = configs['course_thread_expiration_seconds'] if 'course_thread_expiration_seconds' in configs else 3600
        self.active_course_scan_interval_seconds = configs['active_course_scan_interval_seconds'] if 'active_course_scan_interval_seconds' in configs else 60

        # data
        self.base_station_id = base_station_id
        self.cookies_file = cookies_file
        self.valid_course_list = [] 
        self.active_course_threads = {}

        # serial interface
        self.serial_event_lock = threading.Lock()
        self.serial_events = []

    def get_course_color(self) -> list[int]:
        offset = (len(self.active_course_threads)) / self.max_course * 360  # degrees
        print(f"Course color offset: {offset} degrees")
        r = int((math.sin(math.radians(offset + 0)) + 1) / 2 * 255)
        g = int((math.sin(math.radians(offset + 120)) + 1) / 2 * 255)
        b = int((math.sin(math.radians(offset + 240)) + 1) / 2 * 255)

        return [r, g, b]

    def load_cookies_into_session(self, session):

        if not os.path.exists(self.cookies_file):
            raise FileNotFoundError("Cookies file not found. Run interactive login first.")
        cookies = json.load(open(self.cookies_file))
        for c in cookies:
            # requests expects domain without leading dot in some versions; adapt as needed
            session.cookies.set(c['name'], c['value'], domain=c.get('domain'))
        return session

    def scan_valid_courses(self, max_id=1000, verbose=False) -> list[int]:
        '''This function is deprecated. Use get_valid_courses() instead.'''
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
    
    def get_valid_courses(self, verbose=False) -> list[str]:
        self.valid_course_list = []
        s = requests.Session()
        s = self.load_cookies_into_session(s)

        url = "https://eecsoh.eecs.umich.edu/api/courses"
        r = s.get(url, timeout=20)
        courses = r.json()

        for course in courses:
            if verbose:
                print(f"Course ID: {course['id']}, Name: {course['short_name']}")
            for queue in course["queues"]:
                if verbose: print(f"    {queue["id"]}")
                self.valid_course_list.append(queue["id"])
    
    def get_location_from_request(self, request: dict) -> tuple[bool, str]:
        '''Check if the request belongs to this base station and return the location value'''
        location = ""
        try:
            location = request['location']
        except KeyError:
            return False, ""  # 'location' key is missing

        if location == "":
            return False, ""  # location is empty

        if location[0] == self.base_station_id[0]:  # Compare first character
            return True, location
        
        return False, ""
    
    def scan_active_courses(self, verbose: bool = False) -> list[int]:
        active_course_list = []
        s = requests.Session()
        s = self.load_cookies_into_session(s)

        for course_id in self.valid_course_list:
            json_url = f"https://eecsoh.eecs.umich.edu/api/queues/{course_id}"
            r = s.get(json_url, timeout=20)

            session = r.json()
            if not session: continue  # No requests for current course

            if verbose:
                print(f"----------------- scanning course {course_id}---------------") 

            for request in session["queue"]:
                valid, location = self.get_location_from_request(request)

                if valid:
                    if verbose: print(f"Active course ID: {course_id}, location: {location}\n")
                    active_course_list.append(course_id)
                    break  # No need to check further requests for this course

        return active_course_list
    
    def course_thread(self, course_id, course_color, verbose=False):
        s = requests.Session()
        s = self.load_cookies_into_session(s)
        json_url = f"https://eecsoh.eecs.umich.edu/api/queues/{course_id}"

        queued_beacons = {}

        last_active_time = time.time()
        while (time.time() - last_active_time < self.course_thread_expiration_seconds) and self.running:
            r = s.get(json_url, timeout=20)
            if r.status_code != 200:
                raise RuntimeError(f"Failed to fetch JSON: {r.status_code} body: {r.text[:200]}")
            session = r.json()

            if verbose: 
                print("--------------------------------")
                print(f"Fetching course {course_id}")
            
            current_queued_beacon_id = []
            for queue_position, request in enumerate(session["queue"]):
                valid, beacon_id = self.get_location_from_request(request)

                if valid:
                    current_queued_beacon_id.append(beacon_id)

                    # Check for new beacons on the queue or position changes
                    if beacon_id not in queued_beacons or queued_beacons[beacon_id] != queue_position:
                        queued_beacons[beacon_id] = queue_position

                        with self.serial_event_lock:
                            event = {
                                'beacon_id': beacon_id,
                                'queue_position': queue_position,
                                'course_color': course_color
                            }
                            self.serial_events.append(event)

                    last_active_time = time.time()
                    if verbose: print(f"Base station {self.base_station_id} detected beacon_id: {beacon_id} in course {course_id}")

            # Remove beacons that are no longer in the queue
            for beacon_id in list(queued_beacons.keys()):
                if beacon_id not in current_queued_beacon_id:
                    del queued_beacons[beacon_id]

                    with self.serial_event_lock:
                        event = {
                            'beacon_id': beacon_id,
                            'queue_position': -1,  # Indicate removal from queue
                            'course_color': course_color
                        }
                        self.serial_events.append(event)
                    if verbose: print(f"Base station {self.base_station_id} detected beacon_id: {beacon_id} removed from course {course_id}")
            
            time.sleep(self.course_polling_interval_seconds)

        if verbose:
            print(f"Course {course_id} thread expired after {self.course_thread_expiration_seconds} seconds.")
            del self.active_course_threads[course_id]
    
    def spawn_course_thread(self, course_id, verbose=False):
        if verbose:
            print(f"Spawning thread for course {course_id}...")
        t = threading.Thread(target=self.course_thread, args=(course_id, self.get_course_color(), verbose))
        t.start()
        self.active_course_threads[course_id] = t

    def course_thread_manager(self, verbose=False):

        if verbose:
            print("Starting course thread manager...")
        
        while self.running:
            # if we have reached max threads, do not spawn more threads
            
            if verbose:
                print("Scanning for active courses...")

            active_course_list = self.scan_active_courses()
            if verbose:
                print(f"Active courses found: {active_course_list}")
            

            for course_id in active_course_list:
                if len(self.active_course_threads) >= self.max_course:
                    print(f"we have reached max threads: {self.max_course}, not spawning more threads")
                    break

                # If no thread exists for this active course, spawn one
                if course_id not in self.active_course_threads:
                    self.spawn_course_thread(course_id, verbose=verbose)
            time.sleep(self.active_course_scan_interval_seconds)



    def start_course_thread_manager(self, verbose=False):
        self.running = True
        t = threading.Thread(target=self.course_thread_manager, args=(verbose,))
        t.start()
        
            
    
    def get_serial_events(self) -> list[dict]:
        with self.serial_event_lock:
            events = self.serial_events.copy()
            self.serial_events.clear()
        return events
        