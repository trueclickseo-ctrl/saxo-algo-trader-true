# OMX30 Trend-Following Algo — Phase 1: Backtesting

This is **Phase 1 of 4**. It does not place any trades, real or simulated —
it only tests whether the strategy rules would have made money historically.
That's the correct order: prove the logic before risking anything, even
paper money.

## What this system does

A long-only trend-following strategy on OMX30 stocks:
- **Buys** a stock when its 20-day average price crosses above its 50-day
  average (a confirmed uptrend starting)
- **Sells** when the trend reverses, or earlier if the price hits a
  volatility-based stop-loss
- Never risks more than 1% of capital on a single trade
- Never holds more than 5 positions at once
- Has a daily circuit breaker: if the account is down 3% in a day, it
  stops opening new trades until the next day

## How to run it (no coding needed — just follow these steps)

1. **Install Python** if you don't have it: https://www.python.org/downloads/
   (tick "Add Python to PATH" during install on Windows)

2. **Open a terminal** in this folder (on Windows: Shift+Right-click the
   folder → "Open PowerShell window here"; on Mac: right-click → Services
   → "New Terminal at Folder")

3. **Install the dependencies** (one-time):
   ```
   pip install -r requirements.txt
   ```

4. **Run the backtest**:
   ```
   python main.py
   ```

5. Read the results printed in the terminal, and open
   `results/trade_log.csv` in Excel to see every single trade in detail.

## What the results mean

- `total_return_pct` — how much the account grew/shrank over the backtest period
- `max_drawdown_pct` — the worst peak-to-trough loss during the period (this
  tells you how much pain you'd need to tolerate — a strategy with 40%+
  drawdown is not "solid" even if the total return looks good)
- `win_rate_pct` — % of trades that were profitable (trend-following systems
  often have LOW win rates like 30-40% and are still profitable — see below)
- `avg_win` vs `avg_loss` — this ratio is what actually matters, not win rate

## Important, honestly

- Nothing here guarantees future profit. Markets shift. A strategy that
  worked 2018-2024 can stop working. That's why the risk management layer
  (position sizing, stops, daily loss limit) exists — it's there to make
  sure that when the strategy is wrong, it's wrong small.
- This is not financial advice. You are responsible for every trade this
  system ever places, paper or real.
- I'm not a licensed financial advisor — treat this as an engineering
  collaborator, not investment counsel.

## Roadmap (what comes next, once you're happy with backtest results)

1. ✅ **Phase 1 — Backtest** (this): prove the logic on historical data
2. ✅ **Phase 2 — Automated paper trading on Saxo SIM**: `saxo_live_engine.py`
   connects the strategy directly to Saxo's SIM order placement — see below
3. **Phase 3 — Live with minimum capital**: only after Phase 2 shows
   consistent, risk-controlled behavior — connect to your real (small)
   Saxo account
4. **Phase 4 — Monitoring & iteration**: dashboards/alerts so you always
   know what the bot is doing, plus periodic strategy review

## Phase 2 — Automated SIM trading

`saxo_live_engine.py` runs one full decision cycle: fetch current prices,
generate signals, check risk limits and the kill switch, and place real
(SIM/paper) orders on Saxo for anything that passes. It's designed to run
**once per trading day** (see `saxo_live_main.py` for why, and how to
schedule it) — not a polling loop, since the strategy trades on daily bars.

**This is SIM only.** See the safety banner at the top of
`saxo_live_engine.py` — `saxo_client.py` hardcodes Saxo's simulation
gateway; there is no live-trading endpoint anywhere in this project.

**What it does each cycle:**
1. Checks the kill switch and daily loss cap (against Saxo's *real*
   reported equity, not a local estimate)
2. Fetches your actual open positions from Saxo (source of truth — not a
   locally simulated portfolio, since these are real SIM orders)
3. For each held position: checks the ATR stop and trend-reversal exit,
   sells via `place_market_order` if triggered
4. For each signal ticker not already held (up to `MAX_OPEN_POSITIONS`):
   sizes the position with the same risk-based `position_size()` as the
   backtest, checks it against actual cash available, and buys if it fits
5. Logs every order attempt — filled, blocked, or failed — to
   `results/live_order_log.csv`

**Running it:**
```
python saxo_live_main.py
```

**Scheduling it** (so it runs automatically once per day): see the
docstring at the top of `saxo_live_main.py` for Windows Task Scheduler
setup steps.

**Kill switch:** create an empty file named `STOP_TRADING` in this
project's root folder at any time to halt all trading immediately. Delete
it to resume.

**Before this ever becomes Phase 3:** run it for real, for weeks, and read
`results/live_order_log.csv` critically — does it behave the way the
backtest predicted? Do the blocked/failed entries reveal anything about
real order execution the backtest couldn't see (slippage, rejected orders,
liquidity)? Going live should stay a deliberate, separate decision — not
a natural continuation of this file.

## Files in this project

| File | Purpose |
|---|---|
| `config.py` | All settings you might want to change (tickers, risk %, MA periods) |
| `data_loader.py` | Downloads and caches historical price data (backtest only) |
| `live_data.py` | Fetches fresh (uncached) price data for the live engine |
| `strategy.py` | The actual buy/sell rules and position sizing |
| `backtest.py` | Simulates the strategy day-by-day with full risk management |
| `main.py` | Run this to execute a backtest |
| `saxo_auth.py` | One-time PKCE login to Saxo SIM; self-refreshing after that |
| `saxo_client.py` | All Saxo OpenAPI calls (account, positions, balances, orders) |
| `instrument_map.py` | Loads the Yahoo-ticker → Saxo-Uic mapping |
| `kill_switch.py` | Kill switch + daily loss cap state, shared safety logic |
| `saxo_live_engine.py` | Core Phase 2 decision + order-placement logic |
| `saxo_live_main.py` | Run this once per trading day for live SIM trading |
