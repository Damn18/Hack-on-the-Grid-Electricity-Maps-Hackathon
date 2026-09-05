"""Day-ahead price / Actual: settled prices over an explicit time window.

Requires start and end; here the last 24 hours.
https://app.electricitymaps.com/docs/reference/day-ahead-price/actual
"""

from em_client import hours_ago, run

run("price_actual", "actual", {"start": hours_ago(24), "end": hours_ago(0)})
