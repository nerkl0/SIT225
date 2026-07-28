import csv
import time
from datetime import datetime

import serial

PORT = "/dev/ttyACM0"
BAUD = 9600
DURATION_S = 30 * 60  # 2 hours
CSV_PATH = "lux_readings_log.csv"
QUAR_PATH = "lux_quar_log.csv"
SENSOR_MIN, SENSOR_MAX = 1, 1500  # BH1750 valid range in lux

def main():
    # Open the serial port. timeout=2 stops readline() blocking forever if the board stops sending.
    ser_monitor = serial.Serial(PORT, BAUD, timeout=2)
    time.sleep(2)  # small pause for the microcontroller to startup
    ser_monitor.reset_input_buffer()  # discard anything currently sitting in the buffer

    start = time.time()
    data_logged, data_flagged, data_quarantined = 0, 0, 0

    # Two log files created: one for accepted data, one for quarantined data (ie. error/not lux readings)
    with open(CSV_PATH, "w", newline="") as log_file, \
            open(QUAR_PATH, "w", newline="") as quar_file:
        log_writer = csv.writer(log_file)
        log_writer.writerow(["timestamp", "lux", "in_range"])

        quar_writer = csv.writer(quar_file)
        quar_writer.writerow(["timestamp", "raw_line", "reason"])

        try:
            while time.time() - start < DURATION_S:
                reading = ser_monitor.readline().decode(errors="ignore").strip()
                stamp = datetime.now().isoformat(timespec="milliseconds")

                # Skips any blank lines and Arduino comment lines ("[ STATE ]")
                if not reading or reading.startswith("[ "):
                    continue

                # If the line is not parsable as a number, it is serial noise. Quarantine value
                try:
                    lux = float(reading)
                except ValueError:
                    quar_writer.writerow([stamp, reading, "not_numeric"])
                    quar_file.flush()
                    data_quarantined += 1
                    continue

                # Range is flagged as it's outside an outlier. Stays in data log for inspection 
                in_range = SENSOR_MIN <= lux <= SENSOR_MAX
                if not in_range:
                    data_flagged += 1

                log_writer.writerow([stamp, lux, int(in_range)])
                log_file.flush()
                data_logged += 1

                elapsed = (time.time() - start) / 60
                print(f"[{elapsed:5.1f} min] {data_logged:4d} readings  {lux:8.2f} lx",
                      end="\r")

        except KeyboardInterrupt:
            print("\nStopped early by user.")

    ser_monitor.close()
    print(f"\nSaved {data_logged} readings to {CSV_PATH} "
          f"({data_flagged} out of range). "
          f"{data_quarantined} unreadable lines written to {QUAR_PATH}.")


if __name__ == "__main__":
    main()