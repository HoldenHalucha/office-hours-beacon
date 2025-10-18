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

BASE_STATION_ID = "A"

OUT_DIR = "./outstanding_json"

# Absolute path to cookies file
COOKIES_FILE = "C:/Users/jacky/OneDrive - Umich/EECS 473/Project/office-hours-beacon/queueFetcher/oh_cookies.json"

def load_cookies_into_session(session):
    if not os.path.exists(COOKIES_FILE):
        raise FileNotFoundError("Cookies file not found. Run interactive login first.")
    cookies = json.load(open(COOKIES_FILE))
    for c in cookies:
        # requests expects domain without leading dot in some versions; adapt as needed
        session.cookies.set(c['name'], c['value'], domain=c.get('domain'))
    return session

# Scan all course IDs from 0 to max_id and return valid ones as a list
def scan_valid_courses(max_id=1000, verbose=False) -> list[int]:
    valid_id = []
    s = requests.Session()
    s = load_cookies_into_session(s)

    for course_id in range(0, max_id + 1):
        json_url = f"https://oh.eecs.umich.edu/course_queues/{course_id}/outstanding_requests.json"
        r = s.get(json_url, timeout=20)

        if r.status_code == 200:
            if verbose: print(f"Valid course ID: {course_id} status: {r.status_code}")
            valid_id.append(course_id)
        else:
            if verbose: print(f"Invalid course ID: {course_id} status: {r.status_code}")
    
    return valid_id

def scan_active_courses(base_station_id: str, valid_courses: list[int], verbose: bool = False) -> list[int]:
    active_courses = []
    s = requests.Session()
    s = load_cookies_into_session(s)

    for course_id in valid_courses:
        json_url = f"https://oh.eecs.umich.edu/course_queues/{course_id}/outstanding_requests.json"
        r = s.get(json_url, timeout=20)

        queue = r.json()
        if not queue: continue  # No requests for current course

        if verbose:
            print(f"-----------------course {course_id}---------------") 
            print(queue)
        for request in queue:
            location = ""
            try:
                location = request['location']
            except KeyError:
                continue  # Skip if 'location' key is missing

            if location == "":
                continue  # Skip if location is empty

            if location[0] == base_station_id[0]:  # Compare first character
                if verbose: print(f"Active course ID: {course_id}, location: {location}\n")
                active_courses.append(course_id)
                break  # No need to check further requests for this course

    return active_courses


if __name__ == "__main__":
    # Step 1: if you don't have cookies yet, run interactive login once:
    if not os.path.exists(COOKIES_FILE):
        print("Cookie files not found. Exiting...")
        exit(1)
        # print("No cookies found. Starting interactive login to obtain them.")
        # interactive_login_and_save_cookies("https://oh.eecs.umich.edu/")
        # print("Now run this script again (or it will continue to fetch once).")

    # valid_course_id_list = scan_valid_courses(1000)
    # print(f"{len(valid_course_id_list)} valid course IDs found!")
    # print(valid_course_id_list)

    # Precomputed valid course IDs. This list would change if new courses are added to OH queue.
    valid_course_id_list = [1, 3, 7, 8, 14, 15, 21, 24, 25, 26, 30, 33, 34, 35, 38, 41, 42, 43, 46, 48, 49, 50, 52, 53, 54, 58, 60, 61, 62, 65, 66, 67, 68, 71, 72, 73, 92, 93, 95, 96, 97, 100, 102, 105, 106, 121, 123, 125, 128, 130, 132, 133, 134, 140, 141, 143, 146, 150, 151, 152, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 225, 226, 227, 228, 229, 230, 232, 233, 234, 235, 236, 237, 240, 246, 253, 254, 256, 257, 258, 259, 260, 264, 267, 272, 273, 274, 276, 277, 278, 279, 280, 281, 282, 284, 286, 287, 288, 295, 296, 297, 298, 299, 300, 301, 304, 305, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 327, 328, 329, 330, 331, 332, 333, 334, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 368, 370, 371, 372, 380, 382, 383, 384, 385, 388, 390, 391, 392, 394, 395, 396, 397, 398, 399, 403, 404, 405, 406, 407, 408, 409, 413, 414, 417, 418, 419, 420, 421, 425, 426, 431, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 444, 445, 448, 449, 450, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 479, 480, 481, 482, 483, 484, 485, 486, 488, 490, 491, 492, 494, 495, 496, 497, 498, 500, 501, 503, 504, 505, 506, 507, 509, 510, 511, 512, 513, 519, 520, 521, 522, 532, 537, 538, 539, 540, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 561, 562, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582, 583, 584, 588, 589, 590, 591, 592, 593, 594, 595, 598, 601, 602, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 619, 620, 621, 622, 623, 624, 625, 626, 627, 628, 629, 630, 631, 632, 633, 634, 635, 636, 637, 638, 639, 640, 641, 642, 650, 651, 652, 653, 654, 655, 657, 658, 659, 660, 661, 662, 663, 664, 665, 667, 668, 669, 670, 671, 686, 688, 689, 690, 691, 693, 695, 697, 698, 699, 700, 708, 709, 710, 724, 728, 729, 730, 733, 734, 735, 736, 737, 738, 739, 740, 741, 743, 744, 745, 746, 747, 748, 749, 750, 752, 753, 754, 755, 770, 772, 773, 774, 775, 776, 786, 790, 792, 793, 796, 799, 808, 815, 816, 820, 823, 825, 826, 827, 829, 830, 833, 834, 839, 850, 856, 864, 866, 868, 869, 877, 878, 880, 881, 882, 883, 884, 887, 889, 890, 893, 894, 895, 896, 897, 898, 899, 900, 901, 902, 904, 905, 906, 907, 908, 909, 910, 911, 913, 916, 917, 918, 919]

    active_course_id_list = scan_active_courses(BASE_STATION_ID, valid_course_id_list, verbose=True)
    print(f"{len(active_course_id_list)} active course IDs found!")
    print(active_course_id_list)