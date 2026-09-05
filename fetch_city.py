"""Fetch carbon intensity for a city (by coordinates) and save it to a CSV.

Electricity Maps resolves lat/lon to its grid zone (Paris -> FR).
Docs: https://app.electricitymaps.com/docs
"""

import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

CITY = "Paris"
LAT, LON = 48.8566, 2.3522

OUT_DIR = Path(__file__).parent / "0_RESULTS"
OUT_FILE = OUT_DIR / "carbon_intensity.csv"
COLUMNS = ["zone", "carbonIntensity", "datetime"]

resp = requests.get(
    "https://api.electricitymap.org/v3/carbon-intensity/latest",
    params={"lat": LAT, "lon": LON},
    headers={"auth-token": os.environ["EM_TOKEN"]},
    timeout=10,
)
resp.raise_for_status()
data = resp.json()

OUT_DIR.mkdir(exist_ok=True)
is_new = not OUT_FILE.exists()
with OUT_FILE.open("a", newline="") as f:
    writer = csv.writer(f)
    if is_new:
        writer.writerow(["city"] + COLUMNS)
    writer.writerow([CITY] + [data[c] for c in COLUMNS])

print(f"Saved {CITY}: {data['carbonIntensity']} gCO2eq/kWh -> {OUT_FILE}")
