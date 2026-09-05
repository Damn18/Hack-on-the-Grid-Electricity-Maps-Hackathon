"""Probe every Electricity Maps money-data endpoint combination and log
the result (OK or error) of each call to a single log file in 2_LOG.

Covers both API generations, since the naming changed:
  v3: /v3/day-ahead-price/{requestType}
  v4: /v4/price-day-ahead/{requestType}

Docs: https://app.electricitymaps.com/docs/reference/day-ahead-price/actual
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

TOKEN = os.environ["EM_TOKEN"]
HEADERS = {"auth-token": TOKEN}
LOG_FILE = ROOT / "2_LOG" / "price_api_probe.log"

ZONES = ["DK-DK2", "FR", "DE", "ES", "GB", "NL", "PL", "IT-NO"]
REQUEST_TYPES = ["forecast", "actual", "latest", "history", "past", "past-range", "combined"]
APIS = [
    ("v3", "https://api.electricitymap.org/v3/day-ahead-price"),
    ("v4", "https://api.electricitymaps.com/v4/price-day-ahead"),
]

now = datetime.now(timezone.utc)
START = (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:00:00Z")
END = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:00:00Z")

# Extra parameters some request types require on top of ?zone=
EXTRA_PARAMS = {
    "actual": {"start": START, "end": END},
    "history": {},
    "past": {"datetime": START},
    "past-range": {"start": START, "end": END},
    "combined": {},
}


def describe(resp):
    """Short human-readable outcome for the log line."""
    if resp.status_code == 200:
        body = resp.json()
        points = body.get("data", body if isinstance(body, list) else None)
        if isinstance(points, list) and points:
            first = points[0]
            return (f"OK    {len(points):>3} points  "
                    f"first={first.get('value')} {first.get('unit', '')} "
                    f"@ {first.get('datetime')}")
        return f"OK    value={body.get('value')} {body.get('unit', '')} @ {body.get('datetime')}"
    try:
        payload = resp.json()
        return f"FAIL  {payload.get('error') or payload.get('message')}"
    except json.JSONDecodeError:
        return f"FAIL  {resp.text[:120]}"


LOG_FILE.parent.mkdir(exist_ok=True)
lines = [
    f"Electricity Maps price-data probe run at {now.isoformat()}",
    f"{len(APIS)} APIs x {len(REQUEST_TYPES)} request types x {len(ZONES)} zones",
    "=" * 100,
]
summary = {}

for version, base_url in APIS:
    for request_type in REQUEST_TYPES:
        for zone in ZONES:
            params = {"zone": zone, **EXTRA_PARAMS.get(request_type, {})}
            url = f"{base_url}/{request_type}"
            try:
                resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
                status, outcome = resp.status_code, describe(resp)
            except requests.RequestException as exc:
                status, outcome = "ERR", f"FAIL  {exc}"

            summary[(version, request_type)] = summary.get((version, request_type), 0) + (status == 200)
            lines.append(f"{version}  {request_type:<11} {zone:<8} {str(status):<5} {outcome}")
            print(lines[-1])

lines += ["=" * 100, "SUMMARY (zones returning 200 out of %d)" % len(ZONES)]
for (version, request_type), hits in summary.items():
    lines.append(f"  {version}  {request_type:<11} {hits}/{len(ZONES)}")

LOG_FILE.write_text("\n".join(lines) + "\n")
print(f"\n-> {LOG_FILE}")
