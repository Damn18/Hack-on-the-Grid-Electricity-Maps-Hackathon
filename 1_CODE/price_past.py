"""Day-ahead price / Past: prices at one specific datetime.

Uses the 17:00 local window start.
Note: this endpoint is not included in the hackathon token's plan (HTTP 401);
the script is kept so the log records that explicitly.
https://app.electricitymaps.com/docs/reference/day-ahead-price/past
"""

from em_client import START, run, stamp

run("price_past", "past", {"datetime": stamp(START)})
