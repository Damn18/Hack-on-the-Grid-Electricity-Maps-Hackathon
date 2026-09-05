"""Day-ahead price / Modeled: Electricity Maps' modelled price estimates.

Note: not included in the hackathon token's plan (HTTP 401).
https://app.electricitymaps.com/docs/reference/day-ahead-price/modeled
"""

from em_client import run

run("price_modeled", "modeled")
