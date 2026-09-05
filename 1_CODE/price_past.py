"""Day-ahead price / Past: prices at one specific past datetime.

Note: this endpoint is not included in the hackathon token's plan (HTTP 401);
the script is kept so the log records that explicitly.
https://app.electricitymaps.com/docs/reference/day-ahead-price/past
"""

from em_client import hours_ago, run

run("price_past", "past", {"datetime": hours_ago(48)})
