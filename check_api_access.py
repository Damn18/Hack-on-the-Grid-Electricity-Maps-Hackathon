"""Probe every dataType x requestType combination and save the HTTP status
matrix to a CSV, so it is clear which endpoints this token can use.
"""

import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.electricitymap.org/v3"
ZONE = "FR"
DATA_TYPES = [
    "carbon-intensity", "power-breakdown", "power-consumption-breakdown",
    "power-production-breakdown", "day-ahead-price", "renewable-share",
    "fossil-free-share",
]
REQUEST_TYPES = ["forecast", "actual", "latest", "history", "past", "past-range", "combined"]
EXTRA_PARAMS = {
    "past": {"datetime": "2026-09-01T12:00:00Z"},
    "past-range": {"start": "2026-09-01T00:00:00Z", "end": "2026-09-02T00:00:00Z"},
}

OUT_FILE = Path(__file__).parent / "0_RESULTS" / "api_access_matrix.csv"
HEADERS = {"auth-token": os.environ["EM_TOKEN"]}

OUT_FILE.parent.mkdir(exist_ok=True)
with OUT_FILE.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["dataType", "requestType", "status", "available"])

    for data_type in DATA_TYPES:
        for request_type in REQUEST_TYPES:
            params = {"zone": ZONE, **EXTRA_PARAMS.get(request_type, {})}
            resp = requests.get(
                f"{BASE_URL}/{data_type}/{request_type}",
                params=params, headers=HEADERS, timeout=20,
            )
            writer.writerow([data_type, request_type, resp.status_code, resp.status_code == 200])
            print(f"{data_type:<30}{request_type:<12}{resp.status_code}")

print(f"\n-> {OUT_FILE}")
