"""Day-ahead price / Actual: settled prices over an explicit time window.

Requires start and end; here the 24 hours from 17:00 local time.
https://app.electricitymaps.com/docs/reference/day-ahead-price/actual
"""

from em_client import END, START, run, stamp

run("price_actual", "actual", {"start": stamp(START), "end": stamp(END)})
