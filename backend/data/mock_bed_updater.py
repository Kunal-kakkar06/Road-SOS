"""
Mock Bed Updater — simulates live hospital bed changes.
Run in a separate terminal to test SSE real-time updates.

Usage: cd backend && python data/mock_bed_updater.py
"""
import time
import random
import requests

HOSPITALS_URL = "http://localhost:8000/api/hospitals"


def get_hospital_ids():
    res = requests.get(HOSPITALS_URL)
    return [h["id"] for h in res.json()]


def update_randomly():
    print("[MockUpdater] Starting — will update bed counts every 30s")
    ids = get_hospital_ids()
    print(f"[MockUpdater] Found {len(ids)} hospitals")

    while True:
        for hid in ids:
            requests.patch(
                f"{HOSPITALS_URL}/{hid}/beds",
                params={
                    "trauma_beds": random.randint(0, 20),
                    "icu_beds": random.randint(0, 15),
                    "general_beds": random.randint(10, 100),
                },
            )
        print(f"[MockUpdater] Beds updated at {time.strftime('%H:%M:%S')}")
        time.sleep(30)


if __name__ == "__main__":
    update_randomly()
