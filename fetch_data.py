"""Very basic Electricity Maps API fetch.

Docs: https://app.electricitymaps.com/docs
Token is read from the .env file (see .env.example).
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

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
