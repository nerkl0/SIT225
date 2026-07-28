import csv
import time
from datetime import datetime

import serial

PORT = "/dev/ttyACM0"  # Arduino serial port (COM3 etc. on Windows)
BAUD = 9600  # must match Serial.begin(9600) in the sketch
DURATION_S = 30 * 60  # 30 minute session
CSV_PATH = "lux_log.csv"
SENSOR_MIN, SENSOR_MAX = 1, 65535 # BH1750 valid range in lux


def main():
    # Open the serial port. timeout=2 stops readline() blocking forever if the
    # board stops sending.
    ser = serial.Serial(PORT, BAUD, timeout=2)
    time.sleep(2)  # allow the board to reset after the port opens
    ser.reset_input_buffer()  # discard anything already sitting in the buffer

    start = time.time()
    n_kept, n_dropped = 0, 0

    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "lux"]) # header row

        try:
            while time.time() - start < DURATION_S:
                raw = ser.readline().decode(errors="ignore").strip()

                # Skip blank lines and Arduino comment lines (e.g. "# READ_ERROR")
                if not raw or raw.startswith("#"):
                    continue

                # Validation 1: the line must parse as a number
                try:
                    lux = float(raw)
                except ValueError:
                    n_dropped += 1
                    continue

                # Validation 2: the value must sit within the sensor's range
                if not (SENSOR_MIN <= lux <= SENSOR_MAX):
                    n_dropped += 1
                    continue

                writer.writerow([
                    datetime.now().isoformat(timespec="milliseconds"),
                    lux,
                ])
                f.flush()      # write through to disk immediately
                n_kept += 1

                elapsed = (time.time() - start) / 60
                print(f"[{elapsed:5.1f} min] {n_kept:4d} readings  {lux:8.2f} lx",
                      end="\r")

        except KeyboardInterrupt:
            print("\nStopped early by user.")

    ser.close()
    print(f"\nSaved {n_kept} readings to {CSV_PATH}. {n_dropped} rejected.")


if __name__ == "__main__":
    main()