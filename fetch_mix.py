"""Save the current power mix (power-breakdown/latest) per zone to a CSV,
one row per zone/source in MW plus the renewable/fossil-free percentages.
"""

import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.electricitymap.org/v3"
ZONES = ["FR", "DE", "PL", "ES", "GB", "IT-NO", "US-MIDA-PJM", "AU-NSW", "IN-WE"]

OUT_FILE = Path(__file__).parent / "0_RESULTS" / "power_mix_latest.csv"
HEADERS = {"auth-token": os.environ["EM_TOKEN"]}

OUT_FILE.parent.mkdir(exist_ok=True)
with OUT_FILE.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "zone", "datetime", "source", "consumption_MW", "production_MW",
        "renewablePercentage", "fossilFreePercentage",
    ])

    for zone in ZONES:
        resp = requests.get(
            f"{BASE_URL}/power-breakdown/latest",
            params={"zone": zone}, headers=HEADERS, timeout=20,
        )
        resp.raise_for_status()
        d = resp.json()
        consumption = d["powerConsumptionBreakdown"]
        production = d.get("powerProductionBreakdown", {})

        for source in sorted(consumption):
            writer.writerow([
                zone, d["datetime"], source,
                consumption[source], production.get(source, ""),
                d.get("renewablePercentage", ""), d.get("fossilFreePercentage", ""),
            ])

        print(f"{zone:<14} renewable {d.get('renewablePercentage'):>3}%"
              f"   fossil-free {d.get('fossilFreePercentage'):>3}%")

print(f"\n-> {OUT_FILE}")
