"""Day-ahead price / Past range: prices across an arbitrary past interval.

Note: not included in the hackathon token's plan (HTTP 401).
https://app.electricitymaps.com/docs/reference/day-ahead-price/past-range
"""

from em_client import hours_ago, run

run("price_past_range", "past-range", {"start": hours_ago(72), "end": hours_ago(48)})
