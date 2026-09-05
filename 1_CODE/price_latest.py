"""Day-ahead price / Latest: the single most recent price point.

https://app.electricitymaps.com/docs/reference/day-ahead-price/latest
"""

from em_client import run

run("price_latest", "latest")
