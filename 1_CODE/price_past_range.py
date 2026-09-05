"""Day-ahead price / Past range: prices across an explicit interval.

Uses the 24 hours from 17:00 local time.
Note: not included in the hackathon token's plan (HTTP 401).
https://app.electricitymaps.com/docs/reference/day-ahead-price/past-range
"""

from em_client import END, START, run, stamp

run("price_past_range", "past-range", {"start": stamp(START), "end": stamp(END)})
