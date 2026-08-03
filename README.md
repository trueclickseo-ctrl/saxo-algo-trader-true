# ATOS — Algorithmic Trading Operating System
## Agent Handover & Project State Document
### Last Updated: 2026-08-03 | Status: ATOS v1 Built & Tested ✅

---

> **To any Claude agent starting on this project:**
> Read this file top-to-bottom before touching any code.
> It contains everything — architecture, current state, known bugs, decisions made, and what to do next.
> Do NOT make assumptions. Every important decision is documented here with the *reason why*.

---

## 1. What This Project Is

An **automated paper-money algorithmic trading system** connected to a real Saxo Bank SIM (simulation) account via the official Saxo OpenAPI. It runs daily, scans ~71 instruments across 7 markets, makes buy/sell decisions using a 5-detector weighted scoring engine, and **learns from its own trade outcomes** over time.

The owner is building this to:
1. Test and mature algorithmic strategies on paper money before risking real capital
2. Understand which signal detectors work best for which markets
3. Eventually move to live trading once the algo proves itself over weeks/months

**Paper money only. No real money is at risk right now.**

---

## 2. Project Location

```
E:\saxobackup\SaxoTrader\files\     ← ALL code lives here
```

**Git remote:** `https://github.com/trueclickseo-ctrl/saxo-algo-trader-true.git`
**Branch:** `main`
**Live dashboard:** `https://namazic.com/atos/` (auto-uploaded via FTP after each run)

---

## 3. Current System State (as of 2026-08-03)

### ✅ BUILT AND WORKING
| Component | File | Status |
|---|---|---|
| Universe — 71 instruments, 7 markets | `atos/universe.py` | ✅ Working |
| Feature calculator — 10 indicators | `atos/features.py` | ✅ Working |
| 5 Signal Detectors | `atos/detectors.py` | ✅ Working (1 bug fixed, see §9) |
| Decision Engine — weighted voting | `atos/decision_engine.py` | ✅ Working |
| Adaptive Learner — weight updates | `atos/learner.py` | ✅ Working |
| Risk Engine — ATR sizing + gates | `atos/risk.py` | ✅ Working |
| SQLite Database — all tables | `atos/database.py` | ✅ Working, DB exists |
| HTML Dashboard Generator | `atos/dashboard_gen.py` | ✅ Working |
| Daily Runner — full cycle | `atos_runner.py` | ✅ Working |
| FTP upload to namazic.com | Inside `atos_runner.py` | ✅ Working |
| FTP credentials saved | `config/deploy.json` | ✅ Saved permanently |

### ⏳ NEEDS ONE-TIME ADMIN ACTION
| Task | Command | Reason |
|---|---|---|
| Windows Task Scheduler | See §11 | Needs admin PowerShell once |

### ❌ NOT STARTED YET
| Task | Notes |
|---|---|
| Saxo SIM orders for NEW tickers | `instrument_map.csv` only has legacy tickers. New ATOS tickers (GLD, USO, EURUSD etc.) are not yet mapped to Saxo UIC codes. Bot logs signal but skips order for unmapped tickers. |
| `lookup_instruments.py` run for new markets | Must be run once to populate UICs for all ATOS universe tickers |

---

## 4. How The System Works — Full Data Flow

```
Daily Cycle (atos_runner.py)
│
├── 1. Safety checks
│       kill_switch_active()  →  if STOP_TRADING file exists, halt
│       daily_loss_cap_breached()  →  if down >3% today, no new entries
│
├── 2. Download data
│       yfinance → 300 days of OHLCV for all 71 tickers
│
├── 3. Compute features (atos/features.py)
│       Each ticker's DataFrame gets 25+ new columns:
│       ema20, ema50, ema200, atr, adx, rsi, macd, bb_upper/lower/pct,
│       donchian_high/low/breakout_up, vol_ratio, higher_high/low, etc.
│
├── 4. Decision Engine (atos/decision_engine.py)
│       For every ticker:
│         D1_Trend score      (-100 to +100)
│         D2_Momentum score   (-100 to +100)
│         D3_Breakout score   (-100 to +100)
│         D4_MeanReversion score (-100 to +100)  [disabled for Forex/Commodities]
│         D5_Volume score     (-100 to +100)      [neutral if no volume data]
│
│         Combined = weighted average using current weights from DB
│         Score >= 55  →  BUY signal
│         Score <= 20  →  EXIT signal (open positions only)
│
├── 5. Risk Engine (atos/risk.py)
│       For each BUY signal:
│         ✓ Kill switch not active
│         ✓ Daily loss cap not breached
│         ✓ Score >= 55
│         ✓ Total positions < 10
│         ✓ This market group < its cap (US:4, OMX30:2, DAX:2, Commod:2, Forex:2)
│         ✓ ATR available for stop calculation
│         ✓ Position size (ATR-based 1% risk) rounds to >= 1 share
│         ✓ Enough cash to cover cost + commission
│       → If all pass: calculates shares, stop_price, cost_sek
│
├── 6. Place orders (via saxo_client.py — existing infrastructure)
│       Checks instrument_map.csv for Saxo UIC
│       If UIC found: places market order on Saxo SIM
│       If not found: logs signal, skips order (unmapped ticker)
│
├── 7. Check exits
│       For open positions: score <= 20 OR price hit stop_price
│       Places SELL order via saxo_client.py
│
├── 8. Learning pass (atos/learner.py)
│       Reads all closed trades not yet learned from
│       For each: reward/penalise detectors based on was_profitable
│       Saves new weights to DB → they take effect next run
│
├── 9. Equity snapshot → data/atos.db (equity_curve table)
│
├── 10. Generate dashboard/index.html
│        Dark theme, Chart.js equity curve, weight evolution, open positions
│
└── 11. FTP upload → namazic.com/atos/index.html
```

---

## 5. File-by-File Reference

### ATOS v1 (new — the algo system)

| File | Purpose | Key functions |
|---|---|---|
| `atos/universe.py` | 71 instruments across 5 market groups | `ATOS_UNIVERSE`, `market_of(ticker)`, `DETECTOR_MARKET_OVERRIDES` |
| `atos/features.py` | All technical indicators | `add_all(df)` — call this once, get all 25+ columns |
| `atos/detectors.py` | 5 signal detectors, each scoring -100 to +100 | `Detector1_Trend`, `D2_Momentum`, `D3_Breakout`, `D4_MeanReversion`, `D5_Volume` |
| `atos/decision_engine.py` | Weighted combination → BUY/EXIT/HOLD | `evaluate(row, market_group)`, `scan_universe(universe_data, ...)` |
| `atos/learner.py` | Updates weights after closed trades | `run_learning_pass()` — call once per daily cycle after exits |
| `atos/risk.py` | All risk checks and position sizing | `RiskEngine(open_trades)`, `.approve_entry(...)`, `get_risk_capital()` |
| `atos/database.py` | SQLite CRUD — permanent memory | `init_db()`, `insert_trade()`, `close_trade()`, `get_open_trades()`, `get_current_weights()`, `save_weights()`, `upsert_equity()` |
| `atos/dashboard_gen.py` | Generates dashboard/index.html | `generate(todays_actions, open_trades, run_summary)` |
| `atos_runner.py` | **Daily entry point — run this** | `run_cycle()` |
| `test_atos_signal.py` | Diagnostic: shows all detector scores | `python -X utf8 test_atos_signal.py` |
| `config/deploy.json` | FTP credentials for namazic.com (**gitignored**) | Read by `upload_dashboard()` in runner |

### Legacy infrastructure (Phase 1 & 2 — DO NOT MODIFY)
These files work and ATOS depends on some of them. Do not refactor them.

| File | Purpose | Used by ATOS? |
|---|---|---|
| `saxo_auth.py` | Saxo PKCE OAuth login | No (run manually to refresh token) |
| `saxo_client.py` | Saxo API: orders, balances, positions | ✅ Yes — `place_market_order()`, `get_balances()` |
| `saxo_token.json` | OAuth token (**gitignored**, local only) | ✅ Yes — read by saxo_client.py |
| `instrument_map.py` | Loads data/instrument_map.csv (Saxo UICs) | ✅ Yes — needed to place orders |
| `data/instrument_map.csv` | Yahoo ticker → Saxo UIC + currency mapping | ✅ Yes — must expand for new tickers |
| `fx.py` | Currency conversion rates to SEK | ✅ Yes — used in runner for price normalization |
| `kill_switch.py` | Legacy kill switch (original bot) | No — ATOS has its own in risk.py |
| `config.py` | Legacy universe (OMX30 etc.) | No — ATOS uses atos/universe.py |
| `strategy.py` | Legacy EMA crossover strategy | No — ATOS replaces this |
| `saxo_live_engine.py` | Legacy live engine (original single-strategy bot) | No — replaced by atos_runner.py |
| `main.py` | Legacy backtest entry point | No |
| `backtest.py`, `backtest_cfd.py` | Backtesting engines | No |
| `lookup_instruments.py` | Populates instrument_map.csv via Saxo API | ⚠️ Must run for new ATOS tickers |

---

## 6. The Decision Engine — Scoring Logic

### How each detector scores

```
D1 — Trend (EMA + ADX)
  Close > EMA20            +20
  EMA20 > EMA50            +25   ← confirms uptrend
  EMA50 > EMA200           +25   ← confirms long-term bull
  Close > EMA200           +10
  ADX > 30                 +20   ← strong trend
  ADX > 20                 +10   ← moderate trend
  Higher Highs + Higher Lows +10
  Lower Highs + Lower Lows  -20

D2 — Momentum (RSI + MACD)
  RSI crosses above 50     +40   ← STRONGEST momentum signal
  RSI 50-65                +25   ← healthy zone
  RSI > 65                 +10
  RSI < 35 (oversold)      +20
  RSI < 30 (deeply OS)     +30
  MACD > signal AND > 0    +30
  MACD > signal only       +15
  MACD < signal            -15

D3 — Breakout (Donchian 20-day)
  New 20-day HIGH          +80   ← STRONGEST breakout signal
  Top 15% of 20-day range  +40
  Top 40% of range         +15
  New 20-day LOW           -70
  Bottom 15% of range      -40

D4 — Mean Reversion (Bollinger Bands)
  [DISABLED for Forex and Commodities — they trend, not revert]
  BB_pct < 5% AND RSI < 30 +70   ← deeply oversold
  Near lower band + weak   +40
  Above upper band + RSI > 70 (ONLY if NOT in uptrend): -60
  NOTE: if EMA20 > EMA50 (uptrend), being above upper band = NEUTRAL (not penalized)

D5 — Volume
  [NEUTRAL (0) for Forex — no volume data]
  Vol ratio >= 2.0          +50   ← institutional interest
  Vol ratio >= 1.5          +30
  Vol ratio < 0.7           -20
  Vol ratio < 0.5           -35
```

### Thresholds
```python
BUY_THRESHOLD  = 55   # combined score ≥ 55 → BUY
EXIT_THRESHOLD = 20   # combined score ≤ 20 → EXIT open position
```

### Weight learning
- Starts: all weights = 1.0 (equal)
- Updates: after every closed trade via `run_learning_pass()`
- Reward: +0.06 to detectors that correctly predicted direction
- Penalise: -0.04 to detectors that were wrong
- Bounds: min 0.30, max 2.50
- Min trades before learning: 10 (avoids overreacting to early noise)

---

## 7. Market Universe

```python
# 71 instruments total (from atos/universe.py)
# DETECTOR OVERRIDES (important):
# - Forex: Mean Reversion DISABLED, Trend weight ×1.3
# - Commodities: Mean Reversion DISABLED, Breakout weight ×1.3

Market Group    | Instruments                         | Capital Allocation
----------------|-------------------------------------|-------------------
US Equities     | 35 stocks (S&P500 + NASDAQ100)      | 45%
OMX30           | 15 stocks (Swedish blue-chips)      | 15%
DAX40           | 10 stocks (German blue-chips)       | 15%
Commodities     | GLD, SLV, USO, GDX (ETFs)           | 15%
Forex           | EURUSD=X, GBPUSD=X, USDJPY=X        | 10%
```

---

## 8. Risk Rules (All Hard-Coded in atos/risk.py)

```
Starting paper capital:    10,000 SEK
Risk per trade:            1% of risk capital (ATR-based)
Stop loss:                 Entry − 2.5 × ATR (14-day)
Max total positions:       10
Max per market group:      US=4, OMX30=2, DAX=2, Commodities=2, Forex=2
Daily loss cap:            3% — no new entries if ATOS equity down >3% today
Kill switch:               Create file named STOP_TRADING to halt immediately
Min signal score:          55 / 100
Commission model:          0.08% of trade value, min 1 USD (~10 SEK)
```

---

## 9. Known Bugs Fixed (Do Not Re-Introduce)

### Bug #1 — D4 Mean Reversion penalizing trending breakouts ✅ FIXED
**Date:** 2026-08-03 | **Commit:** `7c2dfb8`

**Problem:** MSFT breaking to all-time high (BB_pct=1.28, RSI=74.5) was being penalised -60 by the Mean Reversion detector, pulling combined score from ~68 down to ~45, below the 55 BUY threshold. The bot missed a clear breakout signal.

**Root cause:** D4 was penalising any ticker above the upper Bollinger Band with RSI > 70, even when the stock was in a confirmed uptrend (EMA20 > EMA50). In a trending stock, being above the upper band is a sign of STRENGTH, not overbought.

**Fix:** Added `in_uptrend = (EMA20 > EMA50)` check inside D4. The overbought penalty now ONLY applies when the stock is NOT in an uptrend. In uptrend conditions, D4 returns 0 (neutral) and lets Trend + Breakout detectors handle it.

**File:** `atos/detectors.py` — `Detector4_MeanReversion.score()`

---

### Bug #2 — Live order sizing using Saxo account equity ✅ FIXED (Phase 2)
**Date:** Earlier in Phase 2 | **Commit:** `2f52c30`

**Problem:** Bot was reading live Saxo account balance (~€100,000 SIM money) instead of `config.STARTING_CAPITAL` (10,000 SEK). Position sizes were millions of SEK, Saxo rejected all orders with 400 errors.

**Fix:** Risk capital anchored to `STARTING_CAPITAL_SEK = 10_000` in `atos/risk.py`. Local tracker in `data/atos_risk_state.json` tracks real deployed capital.

---

### Bug #3 — Windows terminal Unicode errors ✅ FIXED
**Problem:** `→`, `✅` and other Unicode characters cause `UnicodeEncodeError` on Windows CP1252 terminal.

**Fix:** Always run with `python -X utf8 script.py` to force UTF-8 output. The Task Scheduler job uses `-X utf8` flag. The test script also sets `sys.stdout.reconfigure(encoding='utf-8')`.

---

## 10. Key Technical Decisions (The "Why")

| Decision | Why |
|---|---|
| **yfinance for data, not Saxo API** | Saxo's historical data API is complex and rate-limited. Yahoo Finance gives clean daily OHLCV for free with excellent coverage. Bot downloads signal data from Yahoo, places orders on Saxo. |
| **SQLite (not PostgreSQL/MySQL)** | Single-user local system. SQLite needs zero server setup, zero credentials, works offline, is faster for reads < 100k rows. Upgrade to Postgres only if remote dashboard needs live DB access. |
| **Static HTML dashboard (not a web app)** | The bot runs locally. A web server on namazic.com would require the DB to be on the server. Static HTML generated locally with data baked in is simpler, more secure, and works offline. |
| **FTP credentials in config/deploy.json (gitignored)** | The machine is used only by the owner. Credentials are stored locally and never leave the machine. The .gitignore protects them from being committed. |
| **`atos/` is independent of legacy `config.py`** | The legacy bot (Phase 2) and ATOS must be able to run independently. ATOS defines its own universe, its own risk rules, its own database. This prevents accidental coupling. |
| **Min 10 trades before weight learning** | With fewer than 10 trades, one lucky/unlucky trade can swing weights dramatically. The warmup period ensures learning starts from a statistically meaningful base. |
| **Redirect URI stays at localhost** | Saxo OAuth PKCE uses `https://localhost/redirect`. This works for local token generation. No need to change it unless the bot needs to run on a remote server (it doesn't). |
| **`instrument_map.csv` is the Saxo UIC bridge** | Yahoo Finance and Saxo use different instrument identifiers. The CSV maps Yahoo tickers to Saxo's internal UIC codes. Without a UIC, no order can be placed. Run `lookup_instruments.py` to populate new UICs. |

---

## 11. How to Run

### First time setup (one-time)
```powershell
pip install -r requirements.txt

# Login to Saxo SIM (OAuth PKCE — opens browser)
python saxo_auth.py

# Map new ATOS tickers to Saxo UICs (needed for orders)
# This queries the Saxo API for each ticker in ATOS universe
# Run from admin PowerShell (it writes to data/instrument_map.csv)
python lookup_instruments.py
```

### Daily run (manually)
```powershell
cd E:\saxobackup\SaxoTrader\files
python -X utf8 atos_runner.py
```

### Task Scheduler (daily at 23:00 — set once, runs forever)
Run this in **Administrator PowerShell** (one time only):
```powershell
$action  = New-ScheduledTaskAction -Execute "python" `
           -Argument "-X utf8 E:\saxobackup\SaxoTrader\files\atos_runner.py" `
           -WorkingDirectory "E:\saxobackup\SaxoTrader\files"
$trigger = New-ScheduledTaskTrigger -Daily -At "23:00"
$settings = New-ScheduledTaskSettingsSet `
           -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
           -RestartCount 1 -RestartInterval (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName "ATOS Daily Run" `
           -Action $action -Trigger $trigger -Settings $settings `
           -Description "ATOS v1 daily algo cycle" -RunLevel Highest -Force
```

### Emergency stop
```powershell
# Create STOP_TRADING file — bot checks for this on every cycle start
New-Item -Path "E:\saxobackup\SaxoTrader\files\STOP_TRADING" -ItemType File

# Resume:
Remove-Item "E:\saxobackup\SaxoTrader\files\STOP_TRADING"
```

### Diagnostic — test signals without placing orders
```powershell
python -X utf8 test_atos_signal.py
```

### View database
```powershell
python -c "
from atos import database as db; db.init_db()
trades = db.get_all_closed_trades()
w = db.get_current_weights()
print(f'Closed trades: {len(trades)}')
print(f'Weights: {w}')
"
```

---

## 12. What To Work On Next (Priority Order)

### Priority 1 — Map ATOS universe to Saxo UICs
**Why:** Right now, ATOS generates signals but cannot place Saxo orders for tickers not in `data/instrument_map.csv`. Only the legacy OMX30/DAX/NASDAQ tickers are mapped. Gold (GLD), Oil (USO), Forex pairs, new US stocks are all unmapped.

**How:** Run `python lookup_instruments.py` — it queries Saxo's reference data API and adds UICs to `data/instrument_map.csv`. May need to handle the new `CfdOnEtc` and `FxSpot` asset types that didn't exist in the Phase 2 implementation.

**Check if UICs are missing:**
```python
from instrument_map import load_instrument_map
from atos.universe import ATOS_UNIVERSE
m = load_instrument_map()
missing = [t for t in ATOS_UNIVERSE if t not in m]
print(f"Missing UICs: {len(missing)} — {missing[:10]}")
```

### Priority 2 — Run first full cycle and fix any runtime errors
```powershell
python -X utf8 atos_runner.py
```
First run will hit `fx.py` for rate lookups and `saxo_client.py` for balances. If token expired, run `python saxo_auth.py` first.

### Priority 3 — Validate dashboard upload to namazic.com
After a successful run, check `https://namazic.com/atos/` loads. If blank, check FTP path in `config/deploy.json` — the `remote_dir` should be `/public_html/atos/`.

### Priority 4 — Backtest ATOS Decision Engine (optional but recommended)
Before trusting live signals, backtest the engine on existing `data/*.csv` historical files. The existing `backtest.py` infrastructure can be adapted or a new `atos/backtest_atos.py` can be created.

---

## 13. Environment Details

```
OS:          Windows 11 (Lenovo ThinkPad)
Python:      3.14 (CPython, 64-bit)
Location:    C:\Users\SEO\AppData\Local\Python\pythoncore-3.14-64\
User:        SEO (standard user — NOT admin by default)
Git:         Configured, pushing to GitHub

Admin note:  User SEO is NOT an administrator. Some operations need
             "Run as Administrator". The .git folder was fixed to allow
             SEO write access (done 2026-08-03).

Installed packages (key):
  yfinance     — market data download
  pandas       — DataFrame operations
  numpy        — numerical calculations
  saxo_client  — custom Saxo OpenAPI wrapper (local file)
```

---

## 14. FTP / Hosting Details

```
Domain:      namazic.com (Hostinger, Custom PHP/HTML plan)
FTP host:    195.35.39.151
FTP port:    21
FTP user:    u104700239.namazic.com
Remote dir:  /public_html/atos/
Credentials: Stored in config/deploy.json (gitignored, local only)
Dashboard:   https://namazic.com/atos/index.html
Upload:      Automatic after each atos_runner.py cycle via ftplib
```

> ⚠️ **Security:** Change the FTP password if you suspect it was exposed. The password was shared in conversation history on 2026-08-03. Go to Hostinger → FTP Accounts → Change FTP Password, then update `config/deploy.json`.

---

## 15. Git Commit History

```
7c2dfb8  fix: D4 MeanReversion no longer penalizes trending breakouts
06ffbc9  feat: ATOS v1 — multi-market self-learning algo trading system
de8781b  Add required ManualOrder field to order payload
a72e939  Document the live-sizing bug fixes in the README
2f52c30  Fix live sizing: anchor risk capital to STARTING_CAPITAL
ac35a61  Add read-only strategy dashboard for monitoring bot decisions
```

---

## 16. Project Roadmap

| Phase | Status | Description |
|---|---|---|
| Phase 1 | ✅ Done | EMA crossover backtest on OMX30, tested on historical data |
| Phase 2 | ✅ Done | Saxo SIM live paper trading, single EMA strategy, bugs fixed |
| **ATOS v1** | ✅ **Current** | Multi-market, self-learning, 5-detector weighted decision engine, dashboard |
| ATOS v2 | 🔒 Future | Add bonds (TLT), sector ETFs, improve D2 with VWAP, add regime detection |
| Phase 3 | 🔒 **Locked** | Live trading — ONLY after 4+ weeks of ATOS paper results showing consistent profit |

> **Phase 3 unlock rule:** Never switch to live money based on code looking good. Read `data/atos.db` trade history with `compare_markets.py`-style analysis. Must show: win rate > 50%, profit factor > 1.5, no single trade > 30% of total profit (concentration check), over minimum 40 closed trades.
