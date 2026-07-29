import csv
import os
import time
from datetime import datetime

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

    # Configure the serial port
    ser = serial.Serial(PORT, BAUD, timeout=2)

    # initialise start as current time and count trackers
    start = time.time()
    logged = quarantined = 0

    # open each csv file in write mode. With title values of timestamp, lux, 
    with open(csv_path, "w", newline="") as log_file, \
            open(quar_path, "w", newline="") as quar_file:
        log_writer = csv.writer(log_file)
        log_writer.writerow(LOG_COLUMN_NAMES)
        quar_writer = csv.writer(quar_file)
        quar_writer.writerow(QUAR_COLUMN_NAMES)

        try:
            while time.time() - start < DURATION:
                # reads serial converting bytes to a string
                serial_data = ser.readline().decode(errors="ignore").strip()
                now = datetime.now().isoformat(timespec="seconds")

                # Skip blank lines and Arduino comment lines ("[ STATE ]")
                if not serial_data or serial_data.startswith("[ "):
                    continue

                try:
                    lux = float(serial_data)
                except ValueError: 
                    # Quarantine any non-numeric lines, into quar_log. Skip to next reading
                    quar_writer.writerow([now, serial_data, "not_numeric"])
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

        ser.close()
        alert() 
        print(f"\nSaved {logged} readings to {csv_path}. "
                f"{quarantined} unreadable lines written to {quar_path}.")

if __name__ == "__main__":
    main()