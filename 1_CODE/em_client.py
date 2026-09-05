"""Shared helpers for the Electricity Maps day-ahead price scripts.

One script per API entrypoint sits next to this module; each of them calls
run() and gets its own CSV in 0_RESULTS and its own log in 2_LOG.

Docs: https://app.electricitymaps.com/docs/reference/day-ahead-price/actual
"""

import csv
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BASE_URL = "https://api.electricitymaps.com/v4/price-day-ahead"
GRANULARITY = "5_minutes"
ZONES = ["DK-DK1", "DK-DK2"]  # Denmark has no single "DK" zone, only the two bidding zones
FIELDS = ["zone", "datetime", "value", "unit", "source", "temporalGranularity"]

NOW = datetime.now(timezone.utc)


def hours_ago(hours):
    return (NOW - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:00Z")


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


def run(name, endpoint, params=None):
    """Call one endpoint for every Danish zone, write a CSV and a log."""
    log, log_file = _logger(name)
    csv_file = ROOT / "0_RESULTS" / f"{name}.csv"
    csv_file.parent.mkdir(exist_ok=True)

    url = f"{BASE_URL}/{endpoint}"
    log.info("endpoint   %s", url)
    log.info("params     temporalGranularity=%s %s", GRANULARITY, params or "")

    rows = []
    for zone in ZONES:
        query = {"zone": zone, "temporalGranularity": GRANULARITY, **(params or {})}
        try:
            resp = requests.get(url, params=query, headers={"auth-token": os.environ["EM_TOKEN"]}, timeout=30)
        except requests.RequestException as exc:
            log.error("%-8s REQUEST FAILED  %s", zone, exc)
            continue

        if resp.status_code != 200:
            log.error("%-8s HTTP %s  %s", zone, resp.status_code, resp.text[:200])
            continue

        points = [p for p in _points(resp.json()) if p.get("datetime")]
        if not points:
            log.warning("%-8s HTTP 200 but no data points returned", zone)
            continue

        rows += [[p.get(f, "") for f in FIELDS] for p in points]
        values = [p["value"] for p in points if p.get("value") is not None]
        log.info(
            "%-8s HTTP 200  %s points  %s -> %s%s", zone, len(points),
            points[0]["datetime"], points[-1]["datetime"],
            f"  range {min(values)} to {max(values)} {points[0].get('unit', '')}" if values else "",
        )

    with csv_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        writer.writerows(rows)

    log.info("wrote %s rows -> %s", len(rows), csv_file)
    log.info("log -> %s", log_file)
    return rows
