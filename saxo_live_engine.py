"""
saxo_live_engine.py
--------------------
Runs ONE decision cycle: fetch current data, generate signals, check risk
limits and the kill switch, and place orders on the Saxo SIM account for
any signal that passes.

============================================================================
WHERE THIS STANDS: SIM (simulation/paper) ONLY
============================================================================
saxo_client.py hardcodes SIM_BASE_URL = "https://gateway.saxobank.com/sim/...".
There is no live-trading base URL anywhere in this project. Orders placed
by this file show up on your Saxo SIM account only — no real money moves.

Moving to Phase 3 (real money) would require deliberately changing the
base URL to Saxo's live gateway, getting a live app key (a separate
approval process from Saxo, not just flipping a setting), and re-doing the
OAuth login against production — none of that exists here. This file
should not be the one that adds it.
============================================================================

WHY THIS RUNS ONCE PER DAY, NOT IN A POLLING LOOP
The strategy operates on DAILY bars (20/50-day moving averages). There is
nothing to gain from checking daily-bar signals every 5 minutes — the
signal doesn't change until a day closes. Run this once per trading day
(see saxo_live_main.py for how to schedule it), ideally after market close
or shortly before the next open.

WHY POSITIONS COME FROM SAXO, NOT A LOCAL FILE
Unlike the Avanza dry-run project (which had to simulate a portfolio
locally, because it wasn't placing real orders), this engine places real
SIM orders — so Saxo's own account IS the source of truth for what's
actually held. get_positions() / get_balances() are queried fresh every
cycle rather than trusting a local state file that could drift out of sync.
"""

import csv
import os
from datetime import datetime

import pandas as pd
import config
from strategy import add_indicators, position_size
from live_data import get_latest_universe_data
from instrument_map import load_instrument_map
import saxo_client
from kill_switch import kill_switch_active, get_day_start_equity, daily_loss_cap_breached
from fx import get_eur_sek_rate

LOG_FILE = os.path.join(os.path.dirname(__file__), "results", "live_order_log.csv")
LOG_FIELDS = ["timestamp", "ticker", "action", "price", "amount", "reason", "order_response"]


def _log(ticker: str, action: str, price, amount, reason: str, order_response=""):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    is_new = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "ticker": ticker, "action": action, "price": price, "amount": amount,
            "reason": reason, "order_response": order_response,
        })


def _get_open_uics(saxo_positions: dict) -> dict:
    """Returns {uic: {'amount': int, 'entry_price': float}} for currently
    open positions on the SIM account, per Saxo's own records."""
    open_uics = {}
    for pos in saxo_positions.get("Data", []):
        base = pos.get("PositionBase", {})
        uic = base.get("Uic")
        amount = base.get("Amount", 0)
        if uic is not None and amount:
            open_uics[uic] = {
                "amount": amount,
                "entry_price": base.get("OpenPrice"),
            }
    return open_uics


def run_cycle():
    print(f"\n{'='*60}\nSaxo SIM live cycle — {datetime.now():%Y-%m-%d %H:%M:%S}\n{'='*60}")

    if kill_switch_active():
        print("STOP_TRADING file present — kill switch active. No action taken.")
        _log("ALL", "HALTED", "", "", "Kill switch active (STOP_TRADING file present)")
        return

    # --- Real account state (source of truth) ---
    balances = saxo_client.get_balances()
    current_equity = balances["TotalValue"]
    cash_available = balances["CashBalance"]
    account_currency = balances.get("Currency", "EUR")
    print(f"Account equity: {current_equity:,.2f} {account_currency}  |  "
          f"Cash available: {cash_available:,.2f} {account_currency}")

    # OMX30 instruments trade in SEK (see data/instrument_map.csv). If the
    # account itself is in a different currency, position sizing and cash
    # checks must compare like-for-like — convert account figures into SEK
    # before using them for sizing. (This assumes a SEK-denominated
    # universe; if config.ACTIVE_UNIVERSE ever trades in a different
    # currency, this conversion needs to change accordingly.)
    if account_currency == "SEK":
        fx_rate = 1.0
    elif account_currency == "EUR":
        fx_rate = get_eur_sek_rate()
        print(f"  EUR/SEK rate: {fx_rate:.4f} (converting account figures to SEK for sizing)")
    else:
        raise RuntimeError(
            f"Account currency is {account_currency}, but only SEK and EUR are "
            f"handled by the fx conversion in this file. Add a conversion for "
            f"{account_currency}/SEK in fx.py before running live."
        )

    equity_sek = current_equity * fx_rate
    cash_available_sek = cash_available * fx_rate

    day_start_equity = get_day_start_equity(current_equity)
    if daily_loss_cap_breached(day_start_equity, current_equity, config.MAX_DAILY_LOSS_PCT):
        print(f"Daily loss cap breached (equity {current_equity:.2f} vs day start "
              f"{day_start_equity:.2f}, cap {config.MAX_DAILY_LOSS_PCT*100:.1f}%). Halting for today.")
        _log("ALL", "HALTED", "", "", f"Daily loss cap breached: {current_equity:.2f} vs {day_start_equity:.2f}")
        return

    saxo_positions = saxo_client.get_positions()
    open_uics = _get_open_uics(saxo_positions)
    print(f"Currently open positions on SIM account: {len(open_uics)}")

    instrument_map = load_instrument_map()

    # --- Fetch data & compute signals ---
    print(f"Fetching latest data for {len(config.ACTIVE_UNIVERSE)} tickers...")
    universe_data = get_latest_universe_data(config.ACTIVE_UNIVERSE)
    universe_data = {t: add_indicators(df) for t, df in universe_data.items()}

    # --- 1. Manage existing positions: exits first ---
    for ticker, info in instrument_map.items():
        uic = info["uic"]
        if uic not in open_uics or ticker not in universe_data:
            continue
        df = universe_data[ticker]
        if df.empty:
            continue
        last_row = df.iloc[-1]
        held = open_uics[uic]

        # Recompute the same ATR-based stop used at entry, off the held entry price
        stop_price = held["entry_price"] - config.ATR_STOP_MULTIPLE * last_row["atr"] \
            if pd.notna(last_row.get("atr")) else None

        hit_stop = stop_price is not None and last_row["Low"] <= stop_price
        trend_broke = bool(last_row.get("cross_down", False))

        if hit_stop or trend_broke:
            reason = "stop_loss" if hit_stop else "trend_reversal"
            print(f"  EXIT signal: {ticker} ({reason}) — selling {held['amount']} units")
            try:
                resp = saxo_client.place_market_order(
                    uic=uic, asset_type="Stock", buy_sell="Sell", amount=held["amount"]
                )
                _log(ticker, "SELL", last_row["Close"], held["amount"], reason, str(resp))
            except Exception as e:
                print(f"    ORDER FAILED: {e}")
                _log(ticker, "SELL-FAILED", last_row["Close"], held["amount"], reason, str(e))

    # --- 2. New entries (only if under the position cap) ---
    open_count = len(open_uics)
    if open_count >= config.MAX_OPEN_POSITIONS:
        print(f"At MAX_OPEN_POSITIONS ({config.MAX_OPEN_POSITIONS}) — skipping new entries this cycle.")
    else:
        for ticker, info in instrument_map.items():
            if open_count >= config.MAX_OPEN_POSITIONS:
                break
            uic = info["uic"]
            if uic in open_uics or ticker not in universe_data:
                continue
            df = universe_data[ticker]
            if df.empty:
                continue
            last_row = df.iloc[-1]

            if not last_row.get("cross_up", False) or pd.isna(last_row.get("atr")):
                continue

            entry_price = last_row["Close"]
            stop_price = entry_price - config.ATR_STOP_MULTIPLE * last_row["atr"]
            amount = position_size(equity_sek, entry_price, stop_price)
            cost_estimate = amount * entry_price

            if amount < 1:
                continue
            if cost_estimate > cash_available_sek:
                print(f"  BUY-BLOCKED: {ticker} would cost ~{cost_estimate:.0f} SEK > "
                      f"cash available {cash_available_sek:.0f} SEK")
                _log(ticker, "BUY-BLOCKED", entry_price, amount,
                     f"Insufficient cash: needs ~{cost_estimate:.0f} SEK, have {cash_available_sek:.0f} SEK")
                continue

            print(f"  ENTRY signal: {ticker} — buying {amount} units @ ~{entry_price:.2f} "
                  f"(stop at {stop_price:.2f})")
            try:
                resp = saxo_client.place_market_order(
                    uic=uic, asset_type="Stock", buy_sell="Buy", amount=amount
                )
                _log(ticker, "BUY", entry_price, amount, "SMA crossover signal", str(resp))
                open_count += 1
                cash_available_sek -= cost_estimate
            except Exception as e:
                print(f"    ORDER FAILED: {e}")
                _log(ticker, "BUY-FAILED", entry_price, amount, "SMA crossover signal", str(e))

    print("\nCycle complete.")


if __name__ == "__main__":
    run_cycle()
