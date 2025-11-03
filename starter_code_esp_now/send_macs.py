import serial
import time
import RPi.GPIO as GPIO

#this pin tells the esp32 to start a read
ESP_SELECT = 23

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(ESP_SELECT, GPIO.OUT)

GPIO.output(ESP_SELECT, GPIO.LOW)

uart = serial.Serial('/dev/serial0', baudrate=9600, timeout=1)

time.sleep(1);

GPIO.output(ESP_SELECT, GPIO.HIGH)

time.sleep(1);

with open('mac_addresses.txt', 'r') as file:
    line_count = sum(1 for _ in file)
print(f"Number of lines: {line_count}")


with open('mac_addresses.txt', 'r') as file:
    while True:
        line = file.readline()
        if not line:  # Break when no more lines
            break
        print(len(line))

        uart.write(line.encode('utf-8'))
        uart.flush()
        time.sleep(0.1)

time.sleep(1)
GPIO.output(ESP_SELECT, GPIO.LOW)
uart.close()
time.sleep(2)
GPIO.cleanup()

