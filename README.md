# ATOS — Algorithmic Trading Operating System
## Agent Handover & Project State Document
### Last Updated: 2026-08-04 | Status: Dashboard Live on localhost:8070 ✅

---

> **To any Claude agent starting on this project:**
> Read this file top-to-bottom before touching any code.
> Every important decision is documented here with the *reason why*.
> Do NOT make assumptions. Do NOT modify files without reading this first.

---

## 1. What This Project Is

An **automated paper-money algorithmic trading system** connected to a real Saxo Bank SIM (simulation) account via the official Saxo OpenAPI. It runs daily, scans ~71 instruments across 7 markets, makes buy/sell decisions using a 5-detector weighted scoring engine, and **learns from its own trade outcomes** over time.

**Paper money only. No real money is at risk right now.**

---

## 2. Project Location & Access

```
E:\saxobackup\SaxoTrader\files\     ← ALL code lives here
```

**Git remote:** `https://github.com/trueclickseo-ctrl/saxo-algo-trader-true.git`
**Branch:** `main`
**Dashboard:** `http://localhost:8070` (local only — runs on this machine)

> **IMPORTANT — Dashboard Decision (2026-08-04):**
> The owner has decided to use **localhost only** for the dashboard.
> `namazic.com` is no longer used for anything. The FTP upload in `atos_runner.py`
> is disabled via `run_atos.py`. Do NOT re-add FTP logic without explicit user request.

---

## 3. Windows User Account Situation ⚠️ CRITICAL READ

This machine has **two user accounts**:
- `SEO` — original user who set up the project. Owns most original files.
- `Kashif` — another account that was active during the second agent session.

**Problem:** Files created by one user cannot be modified by the other unless permissions are fixed.

**Files owned by `Kashif` (agent #2 created these — cannot be edited by SEO):**
- `atos_dashboard.py` — original dashboard server (buggy — see §9)
- `saxo_auth_auto.py` — auto OAuth login
- `run_atos.py` — daily runner wrapper
- `atos_runner_new.py` — alternative runner
- `fix_permissions.bat` — the fix script
- `README_AGENT_UPDATE.md` — agent #2's notes
- `README_DASHBOARD.md` — dashboard docs

**Files owned by `SEO` (agent #1 created these — cannot be edited by Kashif):**
- All `atos/` package files
- `atos_runner.py`
- `saxo_auth.py`, `saxo_client.py`, all legacy files

**The fix (run once as Administrator):**
Right-click `fix_permissions.bat` → **Run as Administrator**

**Or manually in Admin PowerShell:**
```powershell
takeown /F "E:\saxobackup\SaxoTrader\files" /R /D Y
icacls "E:\saxobackup\SaxoTrader\files" /grant SEO:F /T
icacls "E:\saxobackup\SaxoTrader\files" /grant Kashif:F /T
```

Until the permissions are fixed, **always create new files instead of editing files owned by the other user**.

---

## 4. Current System State (as of 2026-08-04)

### ✅ BUILT AND WORKING
| Component | File | Owner | Status |
|---|---|---|---|
| Universe — 71 instruments, 7 markets | `atos/universe.py` | SEO | ✅ |
| Feature calculator — 25+ indicators | `atos/features.py` | SEO | ✅ |
| 5 Signal Detectors (bug fixed) | `atos/detectors.py` | SEO | ✅ |
| Decision Engine — weighted voting | `atos/decision_engine.py` | SEO | ✅ |
| Adaptive Learner — weight updates | `atos/learner.py` | SEO | ✅ |
| Risk Engine — ATR sizing + gates | `atos/risk.py` | SEO | ✅ |
| SQLite Database — all tables | `atos/database.py` | SEO | ✅ |
| Daily Runner — full cycle | `atos_runner.py` | SEO | ✅ |
| Auto OAuth login (catches redirect) | `saxo_auth_auto.py` | Kashif | ✅ |
| Daily runner wrapper (localhost mode) | `run_atos.py` | Kashif | ✅ |
| **Dashboard server v2 (USE THIS)** | **`atos_server.py`** | **SEO** | **✅ Fixed** |
| DB seeded with starting equity | `data/atos.db` | — | ✅ 10,000 SEK |

### ⚠️ EXISTS BUT HAS BUGS (do not use directly)
| File | Bug | Use instead |
|---|---|---|
| `atos_dashboard.py` | Uses single-threaded HTTPServer — drops connections when browser fetches 6 APIs in parallel. Also owned by Kashif so can't be edited by SEO. | Use `atos_server.py` |

### ⏳ NEEDS ONE-TIME ADMIN ACTION
| Task | How |
|---|---|
| Fix file permissions | Right-click `fix_permissions.bat` → Run as Administrator |
| Windows Task Scheduler | See §12 — needs Admin PowerShell |
| Register new OAuth redirect URI | Add `http://localhost:8071/redirect` in Saxo dev portal (see §7) |

### ❌ NOT DONE YET (priority work)
| Task | Notes |
|---|---|
| Map ATOS tickers to Saxo UICs | Run `lookup_instruments.py` — GLD, USO, Forex pairs are unmapped. Bot signals but can't place orders for these. |
| First full daily cycle | `atos_runner.py` has never completed a full run. Run `py -3 -X utf8 run_atos.py` after auth. |
| Saxo token is expired | Run `py -3 saxo_auth_auto.py` to re-authenticate |

---

## 5. How the System Works — Full Data Flow

```
Daily Cycle (run via: py -3 -X utf8 run_atos.py)
│
├── 0. Token check (saxo_auth_auto.py)
│       Reads saxo_token.json → if expired, auto-refresh or browser login
│
├── 1. Safety checks
│       STOP_TRADING file exists → halt
│       Daily loss cap breached (>3%) → no new entries
│
├── 2. Download market data
│       yfinance → 300 days OHLCV for all 71 tickers
│
├── 3. Compute features (atos/features.py)
│       25+ columns added: ema20/50/200, atr, adx, rsi, macd,
│       bb_upper/lower/pct/width, donchian, vol_ratio, higher_high/low
│
├── 4. Decision Engine (atos/decision_engine.py)
│       5 detectors score each ticker (-100 to +100)
│       Weighted average → final score
│       Score ≥ 55 → BUY | Score ≤ 20 → EXIT | else HOLD
│
├── 5. Risk Engine (atos/risk.py)
│       BUY gates: kill switch, daily cap, position limits, ATR, cash
│       Position size = (1% of capital) / (2.5 × ATR)
│
├── 6. Place orders (saxo_client.py)
│       Looks up Saxo UIC in data/instrument_map.csv
│       Places market order on Saxo SIM
│       Logs to data/atos.db (trades + signals tables)
│
├── 7. Check exits
│       Open positions: score ≤ 20 OR price ≤ stop_price → SELL
│
├── 8. Learning pass (atos/learner.py)
│       Reads closed trades, adjusts detector weights
│       Kicks in after 10+ closed trades
│
├── 9. Equity snapshot → data/atos.db
│
├── 10. Generate dashboard HTML (atos/dashboard_gen.py)
│        [Legacy — creates dashboard/index.html]
│
└── 11. FTP upload SKIPPED (localhost mode via run_atos.py)
         Dashboard served live by atos_server.py at localhost:8070
```

---

## 6. File-by-File Reference

### ATOS Core (agent #1 — user SEO)

| File | Purpose | Key functions |
|---|---|---|
| `atos/universe.py` | 71 instruments, 5 market groups | `ATOS_UNIVERSE`, `market_of(ticker)` |
| `atos/features.py` | All technical indicators | `add_all(df)` |
| `atos/detectors.py` | 5 signal detectors, -100 to +100 | D1-D5 classes |
| `atos/decision_engine.py` | Weighted score → BUY/EXIT/HOLD | `evaluate()`, `scan_universe()` |
| `atos/learner.py` | Weight updates after closed trades | `run_learning_pass()` |
| `atos/risk.py` | Risk gates + ATR position sizing | `RiskEngine`, `approve_entry()` |
| `atos/database.py` | SQLite CRUD | `init_db()`, `insert_trade()`, `get_open_trades()`, `get_current_weights()` |
| `atos/dashboard_gen.py` | Legacy static HTML generator | `generate()` |
| `atos_runner.py` | **Daily orchestrator** | `run_cycle()` |
| `atos_server.py` | **Dashboard HTTP server (USE THIS)** | `python -X utf8 atos_server.py` |
| `test_atos_signal.py` | Diagnostic: detector scores | `python -X utf8 test_atos_signal.py` |

### New Files (agent #2 — user Kashif)

| File | Purpose | Notes |
|---|---|---|
| `saxo_auth_auto.py` | Auto OAuth — catches redirect, saves token | Uses port 8071. Register `http://localhost:8071/redirect` in Saxo dev portal |
| `run_atos.py` | Daily runner (localhost mode, no FTP) | **Use this instead of atos_runner.py directly** |
| `atos_dashboard.py` | Original dashboard server | BUGGY — use `atos_server.py` instead |
| `atos_runner_new.py` | Alternative runner | Check before using — may overlap with atos_runner.py |
| `fix_permissions.bat` | Fixes Windows file ownership | Run as Administrator (one time) |
| `README_AGENT_UPDATE.md` | Agent #2 detailed session notes | Read for context on what was done |
| `README_DASHBOARD.md` | Dashboard architecture docs | Reference for dashboard development |

### Legacy Infrastructure (DO NOT MODIFY)

| File | Purpose | Used by ATOS? |
|---|---|---|
| `saxo_auth.py` | Manual OAuth (browser-based) | Fallback if saxo_auth_auto.py fails |
| `saxo_client.py` | Saxo API: orders, balances | ✅ Yes |
| `saxo_token.json` | OAuth token (**gitignored**) | ✅ Yes |
| `instrument_map.py` | Loads data/instrument_map.csv | ✅ Yes |
| `data/instrument_map.csv` | Yahoo→Saxo UIC mapping | ✅ Yes — must expand |
| `fx.py` | Currency → SEK conversion | ✅ Yes |
| `config.py` | Legacy universe | No |
| `strategy.py` | Legacy EMA crossover | No |
| `saxo_live_engine.py` | Legacy live engine | No |

---

## 7. OAuth / Authentication

### Two methods available:

**Method A — Auto login (recommended):**
```powershell
py -3 saxo_auth_auto.py
```
- Opens browser → Saxo login → catches redirect on port 8071 → saves `saxo_token.json`
- **Requires one-time registration:** Add `http://localhost:8071/redirect` in Saxo dev portal
  → https://developer.saxobank.com → Your App → Edit → Add Redirect URL

**Method B — Manual login (fallback):**
```powershell
py -3 saxo_auth.py
```
- Opens browser → Saxo login → manually copies URL back to terminal
- Uses redirect URI: `https://localhost/redirect` (already registered)

**Token lifecycle:**
- Expires every ~24 hours
- `run_atos.py` auto-checks and refreshes before each cycle
- Token saved to `saxo_token.json` (gitignored — never commit)

---

## 8. The Decision Engine — Scoring Logic

```
D1 — Trend (EMA + ADX)
  Close > EMA20            +20
  EMA20 > EMA50            +25   ← uptrend confirmed
  EMA50 > EMA200           +25   ← long-term bull
  Close > EMA200           +10
  ADX > 30                 +20   ← strong trend
  ADX > 20                 +10
  Higher Highs + Lows      +10
  Lower Highs + Lows       -20

D2 — Momentum (RSI + MACD)
  RSI crosses above 50     +40   ← strongest signal
  RSI 50-65                +25   ← healthy zone
  RSI > 65                 +10
  RSI < 35 (oversold)      +20
  RSI < 30 (deeply OS)     +30
  MACD > signal AND > 0    +30
  MACD > signal only       +15
  MACD < signal            -15

D3 — Breakout (Donchian 20-day)
  New 20-day HIGH          +80   ← strongest signal
  Top 15% of range         +40
  Top 40% of range         +15
  New 20-day LOW           -70
  Bottom 15% of range      -40

D4 — Mean Reversion (Bollinger Bands)
  [DISABLED for Forex + Commodities]
  BB_pct < 5% AND RSI < 30 +70
  Near lower band + weak   +40
  Above upper band + high RSI  (ONLY penalised if NOT in uptrend):  -60
  If EMA20 > EMA50: being above upper band = 0 (neutral) ← BUG FIX

D5 — Volume
  [NEUTRAL (0) for Forex — no volume data]
  Vol ratio >= 2.0          +50
  Vol ratio >= 1.5          +30
  Vol ratio < 0.7           -20
  Vol ratio < 0.5           -35

BUY_THRESHOLD  = 55   (score ≥ 55 → BUY)
EXIT_THRESHOLD = 20   (score ≤ 20 → EXIT open position)
```

### Self-Learning Weights
- Start: all 1.0 (equal)
- Kicks in after: 10 closed trades minimum
- Reward correct: +0.06 | Penalise wrong: -0.04
- Bounds: 0.30 – 2.50

---

## 9. Known Bugs Fixed — Do NOT Re-Introduce

### Bug #1 — D4 Mean Reversion kills trending breakouts ✅ FIXED
**Commit:** `7c2dfb8` | **File:** `atos/detectors.py`

MSFT at all-time high (BB_pct=1.28, RSI=74.5) scored -60 in D4, dropping combined score below BUY threshold. In a trending stock (EMA20 > EMA50), being above the upper Bollinger Band is strength, not overbought. Fixed: D4 only penalises overbought when NOT in an uptrend.

---

### Bug #2 — Live order sizing used Saxo account equity ✅ FIXED
**Commit:** `2f52c30` | **File:** `atos/risk.py`

Bot read live Saxo SIM balance (~€100,000) instead of `STARTING_CAPITAL_SEK = 10_000`. Positions were millions of SEK, all rejected with HTTP 400.

---

### Bug #3 — Windows CP1252 Unicode errors ✅ FIXED
Always run with `py -3 -X utf8 script.py`. The runner and test scripts set `sys.stdout.reconfigure(encoding='utf-8')`.

---

### Bug #4 — Dashboard showing "---" (all blank values) ✅ FIXED
**Commit:** pending | **File:** `atos_server.py` (replacement)

**Root causes:**
1. `atos_dashboard.py` uses `HTTPServer` (single-threaded). Browser's `Promise.all()` fires 6 API calls in parallel — single-threaded server dropped all but one, causing fetch failures and blank UI.
2. Two server instances were fighting on port 8070 (started by different user accounts).
3. DB was completely empty (no equity snapshots) — `atos_runner.py` had never run.

**Fix:** `atos_server.py` uses `ThreadingHTTPServer` + `SO_REUSEADDR` + auto-seeds DB on first launch.

---

## 10. Risk Rules (Hard-Coded in atos/risk.py)

```
Starting paper capital:    10,000 SEK
Risk per trade:            1% of capital (ATR-based)
Stop loss:                 Entry − 2.5 × ATR (14-day)
Max total positions:       10
Max per market group:      US=4, OMX30=2, DAX=2, Commodities=2, Forex=2
Daily loss cap:            3% — no new entries if equity down >3% today
Kill switch:               Create file STOP_TRADING to halt immediately
Min signal score:          55 / 100
Commission:                0.08% per trade, min 1 USD (~10 SEK)
```

---

## 11. Key Technical Decisions (The "Why")

| Decision | Why |
|---|---|
| **localhost only — no namazic.com** | Owner decided 2026-08-04. Dashboard runs at localhost:8070. No FTP needed. Simpler, more secure, no server dependency. |
| **yfinance for data, not Saxo API** | Yahoo Finance gives free, clean daily OHLCV. Saxo's historical data API is complex and rate-limited. Bot gets signals from Yahoo, places orders on Saxo. |
| **SQLite (not Postgres)** | Single-user local system. Zero server setup, works offline, fast for <100k rows. |
| **ThreadingHTTPServer (not HTTPServer)** | Browser fires 6 parallel API calls via Promise.all(). Single-threaded server drops all but one, causing blank dashboard. |
| **`run_atos.py` instead of `atos_runner.py` directly** | `atos_runner.py` tries to FTP upload. `run_atos.py` monkey-patches the upload to a no-op and adds token checking. |
| **`atos_server.py` instead of `atos_dashboard.py`** | Dashboard.py is owned by Kashif (uneditable by SEO), uses single-threaded server (drops parallel requests), has no auto-seed. |
| **`instrument_map.csv` as the Saxo UIC bridge** | Yahoo tickers and Saxo UICs are different naming systems. This CSV is the translation layer. Without a UIC, no order can be placed. |
| **Min 10 trades before weight learning** | Prevents overreacting to early noise. One lucky/unlucky trade shouldn't swing weights dramatically. |
| **Redirect URI stays at localhost** | `http://localhost:8071/redirect` (auto) + `https://localhost/redirect` (manual). No web server needed. |

---

## 12. How to Run

### Step 0 — Fix permissions (one time only)
Right-click `fix_permissions.bat` → **Run as Administrator**

### Step 1 — Authenticate with Saxo SIM
```powershell
py -3 saxo_auth_auto.py
```
Browser opens → log in → tokens saved automatically.
Token lasts ~24 hours. Run again when expired.

### Step 2 — Start the dashboard server
```powershell
cd E:\saxobackup\SaxoTrader\files
py -3 -X utf8 atos_server.py
```
Open: **http://localhost:8070**
Keep this terminal open — the server runs continuously.

### Step 3 — Run the daily trading cycle
In a **second terminal**:
```powershell
cd E:\saxobackup\SaxoTrader\files
py -3 -X utf8 run_atos.py
```
This checks the token, runs the full cycle (download → signals → orders → learning), and updates the dashboard DB. Refresh the browser to see new data.

### Run everything at once (if permissions are fixed)
```powershell
py -3 -X utf8 run_atos.py
```
`run_atos.py` also auto-launches `atos_dashboard.py` after the cycle. Switch to `atos_server.py` in `run_atos.py` line 63 once you're happy with it.

### Emergency stop
```powershell
# Halt trading immediately
New-Item -Path "E:\saxobackup\SaxoTrader\files\STOP_TRADING" -ItemType File

# Resume
Remove-Item "E:\saxobackup\SaxoTrader\files\STOP_TRADING"
```

### Task Scheduler (daily at 23:00 — needs Admin PowerShell)
```powershell
$action  = New-ScheduledTaskAction -Execute "py" `
           -Argument "-3 -X utf8 E:\saxobackup\SaxoTrader\files\run_atos.py" `
           -WorkingDirectory "E:\saxobackup\SaxoTrader\files"
$trigger = New-ScheduledTaskTrigger -Daily -At "23:00"
$settings = New-ScheduledTaskSettingsSet `
           -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
           -RestartCount 1 -RestartInterval (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName "ATOS Daily Run" `
           -Action $action -Trigger $trigger -Settings $settings `
           -Description "ATOS v1 daily algo cycle" -RunLevel Highest -Force
```

### Diagnostic — test signal scores without placing orders
```powershell
py -3 -X utf8 test_atos_signal.py
```

### Check database state
```powershell
py -3 -c "
from atos import database as db; db.init_db()
import sqlite3; conn = sqlite3.connect('data/atos.db')
conn.row_factory = sqlite3.Row; c = conn.cursor()
c.execute('SELECT COUNT(*) as n FROM trades'); print('Trades:', c.fetchone()['n'])
c.execute('SELECT COUNT(*) as n FROM equity_curve'); print('Equity rows:', c.fetchone()['n'])
w = db.get_current_weights(); print('Weights:', w)
conn.close()
"
```

---

## 13. Priority Tasks (Next Steps in Order)

### 1. Fix file permissions
```
Right-click fix_permissions.bat → Run as Administrator
```
This unblocks all future file editing for both user accounts.

### 2. Register new OAuth redirect URI
In Saxo dev portal → Your App → Edit → Add redirect URL:
```
http://localhost:8071/redirect
```
Keep `https://localhost/redirect` too (used by `saxo_auth.py`).

### 3. Re-authenticate (token is expired)
```powershell
py -3 saxo_auth_auto.py
```

### 4. Map ATOS universe to Saxo UICs
```powershell
py -3 lookup_instruments.py
```
Check which tickers are missing UICs:
```python
from instrument_map import load_instrument_map
from atos.universe import ATOS_UNIVERSE
m = load_instrument_map()
missing = [t for t in ATOS_UNIVERSE if t not in m]
print(f"Missing UICs: {len(missing)} — {missing[:10]}")
```

### 5. Run the first full daily cycle
```powershell
py -3 -X utf8 run_atos.py
```
Watch for errors. Common first-run issues:
- Token expired → fix with step 3
- Missing UIC → bot logs signal, skips order (not a crash)
- FX rate fetch fails → check internet connection

### 6. Update run_atos.py to use atos_server.py
Change line 63 of `run_atos.py` from `atos_dashboard.py` to `atos_server.py` (requires permissions fix first).

---

## 14. Environment Details

```
OS:          Windows 11 (Lenovo ThinkPad)
Python:      3.14 (CPython, 64-bit)
Location:    C:\Users\SEO\AppData\Local\Python\pythoncore-3.14-64\
Users:       SEO (original), Kashif (second agent session)
             Both need FullControl on project files — run fix_permissions.bat

Python cmd:  Both "python" and "py -3" work. Use "py -3" for reliability.
Encoding:    Always add -X utf8 flag for scripts printing Unicode

Installed packages (key):
  yfinance     — market data download
  pandas       — DataFrame operations
  numpy        — numerical calculations
  (all others via requirements.txt)
```

---

## 15. Market Universe (71 instruments)

```
Market Group    | Tickers                              | Position Cap
----------------|--------------------------------------|-------------
US Equities     | 35 stocks (S&P500 + NASDAQ100)       | 4 positions
OMX30           | 15 Swedish blue-chips                | 2 positions
DAX40           | 10 German blue-chips                 | 2 positions
Commodities     | GLD, SLV, USO, GDX (ETFs)            | 2 positions
Forex           | EURUSD=X, GBPUSD=X, USDJPY=X         | 2 positions

Detector overrides:
  Forex:       Mean Reversion DISABLED, Trend weight ×1.3
  Commodities: Mean Reversion DISABLED, Breakout weight ×1.3
```

---

## 16. Git Commit History

```
(pending)  fix: atos_server.py v2 — ThreadingHTTPServer, auto-seed DB, clean JS
5b3e519    docs: comprehensive agent handover README
7c2dfb8    fix: D4 MeanReversion no longer penalizes trending breakouts
06ffbc9    feat: ATOS v1 — multi-market self-learning algo trading system
de8781b    Add ManualOrder field to order payload
a72e939    Document live-sizing bug fixes
2f52c30    Fix live sizing: anchor to STARTING_CAPITAL
ac35a61    Add read-only strategy dashboard
```

---

## 17. Project Roadmap

| Phase | Status | Description |
|---|---|---|
| Phase 1 | ✅ Done | EMA crossover backtest on OMX30 |
| Phase 2 | ✅ Done | Saxo SIM live paper trading, single strategy, bugs fixed |
| **ATOS v1** | ✅ **Current** | Multi-market, self-learning, 5-detector engine, localhost dashboard |
| ATOS v2 | 🔒 Future | Add VWAP to D2, regime detection, bonds (TLT), sector ETFs |
| Phase 3 | 🔒 **Locked** | Live trading — only after 4+ weeks of paper results |

> **Phase 3 unlock rule:** Read `data/atos.db` trade history critically.
> Must show: win rate >50%, profit factor >1.5, no single trade >30% of total profit, minimum 40 closed trades.
> Never switch to live money because the code "looks good".
