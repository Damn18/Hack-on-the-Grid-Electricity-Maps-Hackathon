"""Fetch the full carbon-intensity timeline (history + forecast) for a zone
and save it to a single CSV in 0_RESULTS.

Docs: https://app.electricitymaps.com/docs
Note: power-breakdown forecast is not included in this API token's plan,
so only carbon intensity is available for future hours.
"""

import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.electricitymap.org/v3"
ZONE = "FR"  # Paris sits in the FR grid zone

OUT_FILE = Path(__file__).parent / "0_RESULTS" / f"carbon_intensity_timeline_{ZONE}.csv"
HEADERS = {"auth-token": os.environ["EM_TOKEN"]}


def get(endpoint, key):
    resp = requests.get(
        f"{BASE_URL}/{endpoint}", params={"zone": ZONE}, headers=HEADERS, timeout=15
    )
    resp.raise_for_status()
    return resp.json()[key]


rows = [("history", p) for p in get("carbon-intensity/history", "history")]
rows += [("forecast", p) for p in get("carbon-intensity/forecast", "forecast")]
rows.sort(key=lambda r: r[1]["datetime"])

OUT_FILE.parent.mkdir(exist_ok=True)
with OUT_FILE.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["zone", "datetime", "carbonIntensity", "type", "isEstimated"])
    for kind, point in rows:
        writer.writerow([
            ZONE,
            point["datetime"],
            point["carbonIntensity"],
            kind,
            point.get("isEstimated", ""),
        ])

values = [p["carbonIntensity"] for _, p in rows]
print(f"{len(rows)} hourly points -> {OUT_FILE}")
print(f"range: {min(values)}-{max(values)} gCO2eq/kWh")
