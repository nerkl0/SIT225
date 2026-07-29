import csv
import os
import time
from datetime import datetime

import shutil
import subprocess
import time

import serial

PORT = "/dev/ttyACM0"
BAUD = 9600
DURATION = 190 * 60 # configures duration of each recording session. X * 60 will convert X minutes into seconds
LOG_DIR = "./logs"
LOG_COLUMN_NAMES =["timestamp", "lux"]
QUAR_COLUMN_NAMES = ["timestamp", "received", "reason"]


def main():
    # create a new log for each session. Stored in logs/ folder within root directory. 
    # titled: {time stamp}_x_log.csv.
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%y%m%d_%H%M")
    csv_path = os.path.join(LOG_DIR, f"{stamp}_lux_log.csv")
    quar_path = os.path.join(LOG_DIR, f"{stamp}_error_log.csv")

    # Configure the serial port, pause briefly for the microcontroller to connect
    # then reset the buffer to remove any garbage values
    ser = serial.Serial(PORT, BAUD, timeout=2)
    time.sleep(2)
    ser.reset_input_buffer()

    start = time.time() # log current start time
    logged = quarantined = 0 # initialise counts for each reading

    alert() 
    # open each csv file in write mode. With title values of timestamp, lux, 
    with open(csv_path, "w", newline="") as log_file, \
            open(quar_path, "w", newline="") as quar_file:
        log_writer = csv.writer(log_file)
        log_writer.writerow(LOG_COLUMN_NAMES)
        quar_writer = csv.writer(quar_file)
        quar_writer.writerow(QUAR_COLUMN_NAMES)

        try:
            while time.time() - start < DURATION:
                reading = ser.readline().decode(errors="ignore").strip()
                now = datetime.now().isoformat(timespec="seconds")

                # Skip blank lines and Arduino comment lines ("[ STATE ]")
                if not reading or reading.startswith("[ "):
                    continue

                try:
                    lux = float(reading)
                except ValueError: 
                    # Quarantine any non-numeric lines, into quar_log. Skip to next reading
                    quar_writer.writerow([now, reading, "not_numeric"])
                    quar_file.flush()
                    quarantined += 1
                    continue
                
                # write log to lux_log
                log_writer.writerow([now, lux])
                log_file.flush()
                logged += 1

                # print reading as output in terminal alongside the time elapsed
                elapsed = (time.time() - start) / 60
                print(f"[{elapsed:5.1f} min] {logged:4d} readings {lux:8.2f} lx", end="\r")

        except KeyboardInterrupt:
            print("\n Detected keyboard press. Stopping recording.")

        finally:
            ser.close()
            alert() 
            print(f"\nSaved {logged} readings to {csv_path}. "
                    f"{quarantined} unreadable lines written to {quar_path}.")


def alert():
    for _ in range(3):
        if shutil.which("paplay"):
            subprocess.run(["paplay", "/usr/share/sounds/freedesktop/stereo/suspend-error.oga"],
                           stderr=subprocess.DEVNULL)
        else:
            print("\a", end="", flush=True)
        time.sleep(0.4)

if __name__ == "__main__":
    main()