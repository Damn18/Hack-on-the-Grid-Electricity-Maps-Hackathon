"""Fetch carbon-intensity history + forecast for several zones into one CSV.

Only these endpoints are available on the hackathon token:
carbon-intensity latest/history/forecast, power-breakdown/latest.
Docs: https://app.electricitymaps.com/docs
"""

import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.electricitymap.org/v3"
ZONES = ["FR", "DE", "PL", "ES", "GB", "IT-NO", "US-MIDA-PJM", "AU-NSW", "IN-WE"]

OUT_FILE = Path(__file__).parent / "0_RESULTS" / "carbon_intensity_zones.csv"
HEADERS = {"auth-token": os.environ["EM_TOKEN"]}


def get(endpoint, key, zone):
    resp = requests.get(
        f"{BASE_URL}/{endpoint}", params={"zone": zone}, headers=HEADERS, timeout=20
    )
    resp.raise_for_status()
    return resp.json()[key]


OUT_FILE.parent.mkdir(exist_ok=True)
with OUT_FILE.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["zone", "datetime", "carbonIntensity", "type"])

    for zone in ZONES:
        points = [("history", p) for p in get("carbon-intensity/history", "history", zone)]
        points += [("forecast", p) for p in get("carbon-intensity/forecast", "forecast", zone)]
        points.sort(key=lambda r: r[1]["datetime"])

        for kind, point in points:
            writer.writerow([zone, point["datetime"], point["carbonIntensity"], kind])

        values = [p["carbonIntensity"] for _, p in points]
        print(f"{zone:<14} {len(points):>3} pts   {min(values):>4}-{max(values):<4} gCO2eq/kWh"
              f"   spread {max(values) - min(values)}")

print(f"\n-> {OUT_FILE}")
