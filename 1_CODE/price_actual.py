from em_client import hours_ago, run

run("price_actual", "actual", {"start": hours_ago(24), "end": hours_ago(0)})
