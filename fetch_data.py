"""Very basic Electricity Maps API fetch.

Docs: https://app.electricitymaps.com/docs
Set your token first:  export EM_TOKEN=your_api_token
"""

import os
import requests

BASE_URL = "https://api.electricitymap.org/v3"
ZONE = "IT"  # e.g. IT, DE, FR

resp = requests.get(
    f"{BASE_URL}/carbon-intensity/latest",
    params={"zone": ZONE},
    headers={"auth-token": os.environ["EM_TOKEN"]},
    timeout=10,
)
resp.raise_for_status()
data = resp.json()

print(f"Zone: {data['zone']}")
print(f"Carbon intensity: {data['carbonIntensity']} gCO2eq/kWh")
print(f"Updated at: {data['datetime']}")
