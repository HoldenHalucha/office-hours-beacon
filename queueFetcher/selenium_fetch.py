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
    valid_course_list = [1, 3, 7, 8, 14, 15, 21, 24, 25, 26, 30, 33, 34, 35, 38, 41, 42, 43, 46, 48, 49, 50, 52, 53, 54, 58, 60, 61, 62, 65, 66, 67, 68, 71, 72, 73, 92, 93, 95, 96, 97, 100, 102, 105, 106, 121, 123, 125, 128, 130, 132, 133, 134, 140, 141, 143, 146, 150, 151, 152, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 225, 226, 227, 228, 229, 230, 232, 233, 234, 235, 236, 237, 240, 246, 253, 254, 256, 257, 258, 259, 260, 264, 267, 272, 273, 274, 276, 277, 278, 279, 280, 281, 282, 284, 286, 287, 288, 295, 296, 297, 298, 299, 300, 301, 304, 305, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 327, 328, 329, 330, 331, 332, 333, 334, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 368, 370, 371, 372, 380, 382, 383, 384, 385, 388, 390, 391, 392, 394, 395, 396, 397, 398, 399, 403, 404, 405, 406, 407, 408, 409, 413, 414, 417, 418, 419, 420, 421, 425, 426, 431, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 444, 445, 448, 449, 450, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 479, 480, 481, 482, 483, 484, 485, 486, 488, 490, 491, 492, 494, 495, 496, 497, 498, 500, 501, 503, 504, 505, 506, 507, 509, 510, 511, 512, 513, 519, 520, 521, 522, 532, 537, 538, 539, 540, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 561, 562, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582, 583, 584, 588, 589, 590, 591, 592, 593, 594, 595, 598, 601, 602, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 619, 620, 621, 622, 623, 624, 625, 626, 627, 628, 629, 630, 631, 632, 633, 634, 635, 636, 637, 638, 639, 640, 641, 642, 650, 651, 652, 653, 654, 655, 657, 658, 659, 660, 661, 662, 663, 664, 665, 667, 668, 669, 670, 671, 686, 688, 689, 690, 691, 693, 695, 697, 698, 699, 700, 708, 709, 710, 724, 728, 729, 730, 733, 734, 735, 736, 737, 738, 739, 740, 741, 743, 744, 745, 746, 747, 748, 749, 750, 752, 753, 754, 755, 770, 772, 773, 774, 775, 776, 786, 790, 792, 793, 796, 799, 808, 815, 816, 820, 823, 825, 826, 827, 829, 830, 833, 834, 839, 850, 856, 864, 866, 868, 869, 877, 878, 880, 881, 882, 883, 884, 887, 889, 890, 893, 894, 895, 896, 897, 898, 899, 900, 901, 902, 904, 905, 906, 907, 908, 909, 910, 911, 913, 916, 917, 918, 919]
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