"""
kill_switch.py
---------------
Same pattern as the Avanza OMX30 project's risk architecture: a kill switch
file that halts all trading instantly, and local persistence of the day's
starting equity so the daily loss circuit breaker (config.MAX_DAILY_LOSS_PCT)
can be checked against Saxo's own reported equity.
"""

import json
import os
from datetime import date

KILL_SWITCH_FILE = os.path.join(os.path.dirname(__file__), "STOP_TRADING")
DAILY_STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "daily_state.json")


def kill_switch_active() -> bool:
    return os.path.exists(KILL_SWITCH_FILE)


def get_day_start_equity(current_equity: float) -> float:
    """
    Returns today's starting equity, initializing it from current_equity
    the first time this is called on a new calendar day. Persisted to disk
    so it survives the script exiting between daily runs.
    """
    os.makedirs(os.path.dirname(DAILY_STATE_FILE), exist_ok=True)
    today = date.today().isoformat()

    state = {}
    if os.path.exists(DAILY_STATE_FILE):
        with open(DAILY_STATE_FILE) as f:
            state = json.load(f)

    if state.get("date") != today:
        state = {"date": today, "day_start_equity": current_equity}
        with open(DAILY_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    return state["day_start_equity"]


def daily_loss_cap_breached(day_start_equity: float, current_equity: float, max_daily_loss_pct: float) -> bool:
    if day_start_equity <= 0:
        return False
    drawdown_pct = (day_start_equity - current_equity) / day_start_equity
    return drawdown_pct >= max_daily_loss_pct
