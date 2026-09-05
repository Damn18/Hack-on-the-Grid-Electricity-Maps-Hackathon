"""Day-ahead price / Forecast: predicted prices for the hours ahead.

https://app.electricitymaps.com/docs/reference/day-ahead-price/forecast
"""

from em_client import run

run("price_forecast", "forecast")
