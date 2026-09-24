import csv
import os
import time
from datetime import datetime
import subprocess
import serial
import firebase_admin
from firebase_admin import credentials, db
import json 

PORT = "/dev/ttyACM0"
BAUD = 9600
DURATION = 720 * 60 # configures duration of each recording session. X * 60 will convert X minutes into seconds
LOG_DIR = "./logs"
log_cols =["timestamp", "lux", "occupied"]
err_cols = ["timestamp", "received", "reason"]
csv_path = os.path.join(LOG_DIR, f"lux_log.csv")
error_path = os.path.join(LOG_DIR, f"error_log.csv")
os.makedirs(LOG_DIR, exist_ok=True)

def main():
    with open("config.json") as f:
        prog = json.load(f)

    ref = firebase_setup(prog, "lux_readings")
    # Configure the serial port
    ser = serial.Serial(PORT, BAUD, timeout=2, exclusive=True)

    # initialise start as current time and count trackers
    start = time.time()
    logged = errors = firebase = 0
    logs, logs_writer = log_open(csv_path, log_cols)
    
    # open each csv file in write mode. With title values of timestamp, lux, 
    with logs:
        try:
            while time.time() - start < DURATION:
                # reads serial converting bytes to a string
                serial_data = ser.readline().decode(errors="ignore").strip()
                now = datetime.now().isoformat(timespec="seconds")
                
                # log errors
                if serial_data.startswith("[ ERROR ]"):
                    error = serial_data.split("]", 1)[-1].strip()
                    log_error([now, serial_data, error])
                    error += 1

                # Skip blank lines and Arduino comment lines ("[ STATE ]")
                if not serial_data or serial_data.startswith("[ "):
                    continue

                try:
                    lux_str, occ_str = serial_data.split(',')
                    lux = None if lux_str == "-" else float(lux_str)
                    occupied = int(occ_str)
                except ValueError: 
                    # Quarantine any non-numeric lines, into error_log.csv. Skip to next reading
                    log_error([now, serial_data, "non_numeric"])
                    errors += 1
                    continue
                
                # write log to lux_log
                log_reading(logs, logs_writer, [now, lux, occupied])
                logged += 1
                
                if ref: 
                    try:
                        ref.push({"timestamp": now, "lux": lux, "occupied": occupied})
                        firebase += 1
                    except Exception:
                        pass

                # print reading as output in terminal alongside the time elapsed
                elapsed = (time.time() - start) / 60
                lux_disp = f"{lux:8.2f}" if lux is not None else f"{'-':>8}"
                print(f"[{elapsed:5.1f} min] {logged:4d} readings {lux_disp} lx", end="\r")

        except KeyboardInterrupt:
            print("\n Detected keyboard press. Stopping recording.")
        finally: 
            ser.close()
            alert()

        print(f"\nSaved {logged} readings to {csv_path}. {errors} unreadable lines.")

def alert():
    for _ in range(3):
        subprocess.run(["paplay", "/usr/share/sounds/freedesktop/stereo/suspend-error.oga"], timeout=3)
        time.sleep(0.5)

def log_open(path, columns):
    new_file = not os.path.exists(path) or os.path.getsize(path) == 0
    fs = open(path, "a", newline="")
    writer = csv.writer(fs)
    if new_file:
        writer.writerow(columns)
    return fs, writer

def log_error(err):
    fs, writer = log_open(error_path, err_cols)
    with fs:
        writer.writerow(err)

def log_reading(fs, writer, row):
    writer.writerow(row)
    fs.flush()

def firebase_setup(cfg, ref):
    cred = credentials.Certificate(cfg["FIREBASE_KEY"])
    firebase_admin.initialize_app(cred, {"databaseURL": cfg["FIREBASE_DB"]})
    try:
        test = db.reference("connection_test")
        test.set({"ts": datetime.now().isoformat()})
        test.delete()
        print("Firebase connected")
    except Exception as e:
        print(f"Firebase connection failed: {e}")
        return None
    return db.reference(ref)

if __name__ == "__main__":
    main()
