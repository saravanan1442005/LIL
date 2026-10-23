"""Mock physical sensor simulator for EcoLifyBuddy live demonstrations.
Periodically emits simulated RFID badge scans, PIR motion pulses, and door opening events
via HTTP webhook to the EcoLifyBuddy backend.
"""
import time
import random
import requests

API_URL = "http://127.0.0.1:5000/api/v2/sensors/event"

SENSORS = [
    {
        "sensor_id": "GATE-1-PIR",
        "sensor_type": "PIR",
        "zone_id": 1,
        "payload": {"motion_detected": True, "sensitivity": 0.85, "location": "Turnstile North"}
    },
    {
        "sensor_id": "GATE-1-RFID",
        "sensor_type": "RFID",
        "zone_id": 1,
        "payload": {"rfid_tag": "TAG-882194", "reader": "HID-iClass-01", "access": "GRANTED"}
    },
    {
        "sensor_id": "DOOR-B2-MAG",
        "sensor_type": "DOOR",
        "zone_id": 1,
        "payload": {"contact_open": True, "door_id": "Emergency Exit 2"}
    },
    {
        "sensor_id": "GATE-2-QR",
        "sensor_type": "QR",
        "zone_id": 1,
        "payload": {"qr_pass": "GUEST-PASS-9902", "valid": True, "host_flat": "304"}
    }
]


def run_sensor_simulation(iterations: int = 5, delay_seconds: float = 2.0):
    print(f"[*] Starting sensor simulator targeting: {API_URL}")
    print(f"[*] Emitting {iterations} simulated IoT sensor pulses...")

    for i in range(1, iterations + 1):
        s = random.choice(SENSORS)
        body = {
            "sensor_id": s["sensor_id"],
            "sensor_type": s["sensor_type"],
            "zone_id": s["zone_id"],
            "event_data": s["payload"]
        }

        try:
            res = requests.post(API_URL, json=body, timeout=5)
            if res.status_code == 201:
                print(f"[{i}/{iterations}] [OK] Dispatched {s['sensor_type']} Event from '{s['sensor_id']}' -> HTTP 201")
            else:
                print(f"[{i}/{iterations}] [WARN] Received HTTP {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[{i}/{iterations}] [ERR] Connection error (is web server running?): {e}")

        time.sleep(delay_seconds)

    print("[DONE] Sensor simulation completed.")


if __name__ == "__main__":
    run_sensor_simulation()
