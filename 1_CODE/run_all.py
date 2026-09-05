"""Run every day-ahead price entrypoint script in turn."""

import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "price_forecast.py", "price_actual.py", "price_latest.py", "price_history.py",
    "price_past.py", "price_past_range.py", "price_combined.py", "price_modeled.py",
]

here = Path(__file__).parent
for script in SCRIPTS:
    print(f"\n{'=' * 70}\n{script}\n{'=' * 70}")
    subprocess.run([sys.executable, str(here / script)], check=False)
