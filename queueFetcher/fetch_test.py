"""
fetch_test.py
This file is created for testing on pc only. Actual production ready script is selenium_fetch.py
"""

from fetcher import Fetcher
import os
import time
from functools import wraps

BASE_STATION_ID = "A"

# Absolute path to cookies file
COOKIES_FILE = "C:/Users/jacky/OneDrive - Umich/EECS 473/Project/office-hours-beacon/queueFetcher/oh_cookies.json"

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
    'max_course': 2,
    'course_polling_interval_seconds': 2,
    'course_thread_expiration_seconds': 10,
    'active_course_scan_interval_seconds': 5
}

if __name__ == "__main__":
    # Step 1: if you don't have cookies yet, run interactive login once:
    if not os.path.exists(COOKIES_FILE):
        print("Cookie files not found. Exiting...")
        exit(1)
    
    fetcher = Fetcher(BASE_STATION_ID, COOKIES_FILE, configs=fetcher_configs)

    # Precomputed valid course IDs. This list would change if new courses are added to OH queue.
    valid_course_list = [808, 815, 816, 820, 823, 825, 826, 827, 829, 830, 833, 834, 839, 850, 856, 864, 866, 868, 869, 877, 878, 880, 881, 882, 883, 884, 887, 889, 890, 893, 894, 895, 896, 897, 898, 899, 900, 901, 902, 904, 905, 906, 907, 908, 909, 910, 911, 913, 916, 917, 918, 919]

    fetcher.valid_course_list = valid_course_list

    fetcher.start_course_thread_manager(verbose=False)

    try:
        while True:
            time.sleep(2)
            events = fetcher.get_serial_events()

            message = "S"
            for event in events:
                message += f"#{event['beacon_id']}%{event['queue_position']}%{event['course_color']}"
            message += "Z"
            
            print(message)

    except KeyboardInterrupt:
        print("Stopping fetcher...")
        fetcher.running = False