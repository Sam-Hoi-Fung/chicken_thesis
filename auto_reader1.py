import time
import json
import csv
import os
import logging
import argparse
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta
from reader import CF816Reader

# Logging for errors only
logging.basicConfig(
    filename="reader1_debug.log",
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# MQTT setup
mqtt_client = mqtt.Client()
mqtt_client.connect("45.157.177.232", 1883)
mqtt_client.loop_start()

def on_disconnect(client, userdata, rc):
    logging.error(f"MQTT disconnected with result code {rc}")
    print(f"MQTT disconnected with result code {rc}")

mqtt_client.on_disconnect = on_disconnect

def upload_to_server(data):
    try:
        payload = json.dumps(data)
        mqtt_client.publish("rfid/coop", payload)
    except Exception as e:
        logging.error(f"MQTT publish error: {e}")
        print(f"MQTT publish error: {e}")

def get_config():
    parser = argparse.ArgumentParser(description="RFID reader configuration")
    parser.add_argument("--port", required=True, help="USB port for reader (e.g. /dev/ttyUSB0)")
    parser.add_argument("--power", type=int, default=30, help="Power level (10-33 dBm)")
    parser.add_argument("--antennas", default="1,2,7,8", help="Comma-separated list of ports to scan")
    parser.add_argument("--interval", type=float, default=0.1, help="Scan interval in seconds")

    args = parser.parse_args()

    ports = []
    for p in args.antennas.split(','):
        try:
            port = int(p.strip())
            if 1 <= port <= 8:
                ports.append(port)
        except ValueError:
            continue

    return {
        'port': args.port,
        'power_level': args.power,
        'active_ports': ports,
        'scan_interval': args.interval
    }

def log_detection(port, eid, timestamp):
    entry = {
        "timestamp": timestamp,
        "antenna": f"Ant_{port}",
        "eid": eid,
        "device": "Reader_1_coop_2"
    }

    filename = f"{datetime.now().strftime('%Y-%m-%d')}.csv"
    try:
        write_header = not os.path.exists(filename)
        with open(filename, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=entry.keys())
            if write_header:
                writer.writeheader()
            writer.writerow(entry)
    except Exception as e:
        logging.error(f"CSV logging error: {e}")
        print(f"CSV logging error: {e}")

    upload_to_server(entry)

# ----------------------
# Movement Tracking Logic
# ----------------------

# Track last seen data for each EID
last_seen = {}

# Define gate pairs: key is interior, value is matching exterior
GATE_PAIRS = {
    1: 8,
    8: 1,
}

# Timeout in seconds (1 hour)
TIMEOUT_SECONDS = 3600

def should_log_event(current_port, eid):
    now = time.time()
    last_info = last_seen.get(eid)

    if last_info is None:
        # First time seeing EID
        last_seen[eid] = (current_port, now)
        return True

    last_port, last_time = last_info

    # If same antenna and timeout not exceeded → skip
    if current_port == last_port and (now - last_time) < TIMEOUT_SECONDS:
        return False

    # If moved across the gate (e.g., 1 <-> 2), log and update
    if GATE_PAIRS.get(last_port) == current_port:
        last_seen[eid] = (current_port, now)
        return True

    # If timeout exceeded even on same side, log again
    if (now - last_time) >= TIMEOUT_SECONDS:
        last_seen[eid] = (current_port, now)
        return True

    # Not a meaningful movement
    return False

def main():
    config = get_config()
    reader = CF816Reader(config['port'], 57600)

    if not reader.set_rf_power(config['power_level']):
        logging.error("Failed to initialize reader!")
        print("Failed to initialize reader!")
        reader.close()
        return

    print(f"\nStarting RFID Reader 1 with:")
    print(f"Power: {config['power_level']}dBm")
    print(f"Ports: {config['active_ports']}")
    print(f"Scan Interval: {config['scan_interval']}s")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            for port in config['active_ports']:
                eids = reader.send_and_receive_once(port)
                for eid in eids:
                    if should_log_event(port, eid):
                        log_detection(port, eid, timestamp)
            time.sleep(config['scan_interval'])

    except KeyboardInterrupt:
        print("\nStopping reader...")
    finally:
        reader.close()

if __name__ == "__main__":
    main()
