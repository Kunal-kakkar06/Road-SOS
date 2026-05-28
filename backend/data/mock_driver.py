"""
Mock Driver Location Updater
Simulates a driver moving toward the patient for testing SSE live tracking.

Usage:
  cd backend && python data/mock_driver.py <ambulance_id> <patient_lat> <patient_lng>

Example:
  python data/mock_driver.py 1 12.9716 77.5946
"""
import time
import math
import requests
import sys

BACKEND = "http://localhost:8000"


def simulate_driver(provider_id: str, patient_lat: float, patient_lng: float):
    """Moves driver toward patient, posting GPS every 5 seconds."""
    # Start 2km north-east of patient
    lat = patient_lat + 0.018
    lng = patient_lng + 0.018

    print(f"🚑 Simulating driver (provider {provider_id}) → ({patient_lat}, {patient_lng})")
    print(f"   Starting at ({lat:.5f}, {lng:.5f})")
    print()

    for step in range(60):  # max 5 min simulation
        # Move 10% closer each step
        lat = lat + (patient_lat - lat) * 0.1
        lng = lng + (patient_lng - lng) * 0.1

        try:
            res = requests.post(
                f"{BACKEND}/api/ambulance/location",
                json={
                    "provider_id": provider_id,
                    "lat": lat,
                    "lng": lng
                },
            )
            dist = math.sqrt((lat - patient_lat) ** 2 + (lng - patient_lng) ** 2) * 111
            status = "✓" if res.status_code == 200 else f"✗ {res.status_code}"
            print(f"  Step {step + 1:2d}: {dist:.3f} km away  {status}")

            if dist < 0.05:  # within 50m = arrived
                print()
                print("  ✅ Driver arrived at patient location!")
                break
        except Exception as e:
            print(f"  Step {step + 1:2d}: Error: {e}")

        time.sleep(5)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python data/mock_driver.py <provider_id> <patient_lat> <patient_lng>")
        print("Example: python data/mock_driver.py some-uuid-string 12.9716 77.5946")
        sys.exit(1)

    provider_id = sys.argv[1]
    patient_lat = float(sys.argv[2])
    patient_lng = float(sys.argv[3])
    simulate_driver(provider_id, patient_lat, patient_lng)

