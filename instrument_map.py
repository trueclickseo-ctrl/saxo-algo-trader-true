"""
instrument_map.py
------------------
Loads data/instrument_map.csv — the mapping between Yahoo Finance tickers
(used for backtesting/signal data) and Saxo's internal Uic codes (needed to
place orders). Built by lookup_instruments.py.
"""

import csv
import os

MAP_FILE = os.path.join(os.path.dirname(__file__), "data", "instrument_map.csv")


def load_instrument_map() -> dict:
    """Returns {yahoo_ticker: {'uic': int, 'symbol': str}} for every mapped ticker."""
    if not os.path.exists(MAP_FILE):
        raise FileNotFoundError(
            f"{MAP_FILE} not found. Run lookup_instruments.py first to build it."
        )
    mapping = {}
    with open(MAP_FILE) as f:
        for row in csv.DictReader(f):
            if not row.get("uic"):
                continue  # skip tickers flagged needs_review / unmapped
            mapping[row["yahoo_ticker"]] = {
                "uic": int(row["uic"]),
                "symbol": row["symbol"],
            }
    return mapping
