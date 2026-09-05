"""Fetch day-ahead prices (v4) for several zones and save them to a CSV.

Uses the 'combined' request type: one call per zone returns settled prices
sliding into forecast prices on a single hourly timeline.
Docs: https://app.electricitymaps.com/docs/reference/day-ahead-price/actual
"""

import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE_URL = "https://api.electricitymaps.com/v4/price-day-ahead/combined"
ZONES = ["DK-DK2", "FR", "DE", "ES", "GB", "NL", "PL", "IT-NO"]

OUT_FILE = ROOT / "0_RESULTS" / "day_ahead_price.csv"
HEADERS = {"auth-token": os.environ["EM_TOKEN"]}

OUT_FILE.parent.mkdir(exist_ok=True)
with OUT_FILE.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["zone", "datetime", "value", "unit", "source"])

    for zone in ZONES:
        resp = requests.get(BASE_URL, params={"zone": zone}, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        points = resp.json()["data"]

        for point in points:
            writer.writerow([
                zone, point["datetime"], point["value"],
                point.get("unit", ""), point.get("source", ""),
            ])

        values = [p["value"] for p in points]
        print(f"{zone:<8} {len(points):>3} pts   {min(values):>8.2f} to {max(values):>8.2f} "
              f"{points[0].get('unit', '')}   spread {max(values) - min(values):.2f}")

print(f"\n-> {OUT_FILE}")
