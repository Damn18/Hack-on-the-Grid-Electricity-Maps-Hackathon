"""Day-ahead price / History: the rolling recent window of past prices.

https://app.electricitymaps.com/docs/reference/day-ahead-price/history
"""

from em_client import run

run("price_history", "history")
