"""Day-ahead price / Combined: settled and forecast prices on one timeline.

The most useful entrypoint for scheduling: past and future in a single call.
https://app.electricitymaps.com/docs/reference/day-ahead-price/combined
"""

from em_client import run

run("price_combined", "combined")
