"""Shared helpers for the Electricity Maps day-ahead price scripts.

One script per API entrypoint sits next to this module; each of them calls
run() and gets its own CSV in 0_RESULTS and its own log in 2_LOG.

All data is fetched from 17:00 local time (Europe/Copenhagen) onwards:
that instant is the window start for the endpoints that take start/end, and
points before it are dropped from the endpoints that do not.

Docs: https://app.electricitymaps.com/docs/reference/day-ahead-price/actual
"""

import csv
import logging
import os
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE_URL = "https://api.electricitymaps.com/v4/price-day-ahead"
GRANULARITY = "15_minutes"
ZONES = ["DK-DK1", "DK-DK2"]  # Denmark has no single "DK" zone, only the two bidding zones
FIELDS = ["zone", "datetime", "value", "unit", "source", "temporalGranularity"]

LOCAL_TZ = ZoneInfo("Europe/Copenhagen")
START_HOUR = 17
WINDOW_HOURS = 24

# Re-running a script with an attempt number retries the same endpoint at a
# different granularity and writes to separate files, e.g.
#   python price_past.py 2   ->  price_past_2ATTEMPT.{csv,log} at 5_minutes
ATTEMPTS = {"2": "5_minutes"}


def _window():
    """Today 17:00 local time, and the 24 hours that follow, in UTC."""
    today = datetime.now(LOCAL_TZ).date()
    start = datetime.combine(today, time(START_HOUR), tzinfo=LOCAL_TZ)
    return start.astimezone(timezone.utc), (start + timedelta(hours=WINDOW_HOURS)).astimezone(timezone.utc)


START, END = _window()


def stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:00Z")


def hours_before_start(hours):
    """A timestamp measured back from the 17:00 window start."""
    return stamp(START - timedelta(hours=hours))


def _logger(name):
    log_file = ROOT / "2_LOG" / f"{name}.log"
    log_file.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        handlers=[logging.FileHandler(log_file, mode="w"), logging.StreamHandler()],
    )
    return logging.getLogger(name), log_file


def _points(payload):
    """Normalise the three response shapes into a list of points."""
    if isinstance(payload, list):
        return payload
    for key in ("data", "history", "forecast"):
        if key in payload:
            return payload[key]
    return [payload]  # 'latest' returns a single bare object


def _attempt():
    """Read an optional attempt number from the command line."""
    number = sys.argv[1] if len(sys.argv) > 1 else None
    if number is None:
        return "", GRANULARITY
    if number not in ATTEMPTS:
        raise SystemExit(f"unknown attempt {number!r}, expected one of {sorted(ATTEMPTS)}")
    return f"_{number}ATTEMPT", ATTEMPTS[number]


def run(name, endpoint, params=None):
    """Call one endpoint for every Danish zone, write a CSV and a log.

    Previous attempts are never overwritten: attempt 2 writes its own
    *_2ATTEMPT.csv and *_2ATTEMPT.log alongside the originals.
    """
    suffix, granularity = _attempt()
    name = f"{name}{suffix}"
    log, log_file = _logger(name)
    csv_file = ROOT / "0_RESULTS" / f"{name}.csv"
    csv_file.parent.mkdir(exist_ok=True)

    url = f"{BASE_URL}/{endpoint}"
    log.info("endpoint   %s", url)
    log.info("params     temporalGranularity=%s %s", granularity, params or "")
    log.info("window     from %s (17:00 %s) onwards", stamp(START), LOCAL_TZ.key)

    rows = []
    for zone in ZONES:
        query = {"zone": zone, "temporalGranularity": granularity, **(params or {})}
        try:
            resp = requests.get(url, params=query, headers={"auth-token": os.environ["EM_TOKEN"]}, timeout=30)
        except requests.RequestException as exc:
            log.error("%-8s REQUEST FAILED  %s", zone, exc)
            continue

        if resp.status_code != 200:
            log.error("%-8s HTTP %s  %s", zone, resp.status_code, resp.text[:200])
            continue

        returned = [p for p in _points(resp.json()) if p.get("datetime")]
        points = [p for p in returned if p["datetime"] >= stamp(START)]
        dropped = len(returned) - len(points)

        if not points:
            log.warning("%-8s HTTP 200 but nothing at or after the window start "
                        "(%s points returned, all earlier)", zone, len(returned))
            continue

        rows += [[p.get(f, "") for f in FIELDS] for p in points]
        values = [p["value"] for p in points if p.get("value") is not None]
        log.info(
            "%-8s HTTP 200  %s points kept (%s dropped before 17:00)  %s -> %s%s",
            zone, len(points), dropped, points[0]["datetime"], points[-1]["datetime"],
            f"  range {min(values)} to {max(values)} {points[0].get('unit', '')}" if values else "",
        )

    with csv_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        writer.writerows(rows)

    log.info("wrote %s rows -> %s", len(rows), csv_file)
    log.info("log -> %s", log_file)
    return rows
