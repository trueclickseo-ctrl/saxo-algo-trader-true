# ATOS — Algorithmic Trading Operating System
## Agent Handover & Project State Document
### Last Updated: 2026-08-04 02:53 PKT | Updated by: Agent #4 (Full System Audit)

---

> ## 🤖 MULTI-AGENT PROTOCOL — READ FIRST
>
> **5 Claude agents share this project. Before doing ANYTHING:**
>
> 1. `git pull origin main` — get latest code
> 2. Read this entire README
> 3. Do your work
> 4. Update this README with what you did and what's next
> 5. `git add -A && git commit -m "agent: <what you did>" && git push origin main`
>
> **Every agent MUST push to git before ending their session. No exceptions.**
> If you don't push, the next agent starts blind.

---

## 1. What This Project Is

An **automated paper-money algorithmic trading system** on a Saxo Bank SIM (simulation) account via the official Saxo OpenAPI. Runs daily, scans 71 instruments across 5 markets, makes BUY/EXIT decisions using 5 weighted signal detectors, and **self-learns** from closed trade outcomes.

**Paper money only. No real money at risk.**

---

## 2. Project Location

```
Local:  E:\saxobackup\SaxoTrader\files\    ← ALL code lives here
Git:    https://github.com/trueclickseo-ctrl/saxo-algo-trader-true.git
Branch: main
Dashboard: http://localhost:8070           ← localhost only (no web hosting)
```

---

## 3. Current System State — 2026-08-04 02:53 PKT

### ✅ WORKING RIGHT NOW
| What | How | Notes |
|---|---|---|
| Dashboard live | `py -3 -X utf8 atos_server.py` | http://localhost:8070 |
| 4 open positions visible | Synced from Saxo SIM | PRX.AS, NIBE-B.ST, HEXA-B.ST, HM-B.ST |
| Active DB | `data/atos_live.db` | SEO-owned, writable, has 4 trades |
| All 5 ATOS detectors | `atos/detectors.py` | D4 bug fixed |
| Decision engine | `atos/decision_engine.py` | BUY>=55, EXIT<=20 |
| Adaptive learner | `atos/learner.py` | Kicks in after 10 closed trades |

### 🔴 CRITICAL — Agent #4 Audit Findings
| Finding | Severity | Details |
|---|---|---|
| **risk.py equity/cash conflation bug** | 🔴 CRITICAL | `risk_capital_sek` tracks cash not equity — daily loss cap false-triggers after 2-3 buys, position sizing shrinks, equity curve wrong |
| **Engine has NEVER run** | 🔴 CRITICAL | `last_run_date: null` — zero daily cycles executed |
| **4 positions placed manually** | ⚠️ HIGH | Agent #2 placed them on Saxo SIM directly — no detector scores, no algorithmic basis |
| **No stop-losses on any position** | ⚠️ HIGH | Engine never ran, so ATR stops were never set |
| **Decision engine rated 5/10** | ⚠️ MEDIUM | Good foundation but needs regime detection, trailing stops, correlation checks |

### ⚠️ KNOWN ISSUES — MUST FIX
| Issue | Cause | Fix |
|---|---|---|
| **Bug #5 — risk.py equity/cash conflation** | `record_fill()` subtracts position cost from `risk_capital_sek`, treating it as cash not equity | Separate cash tracking from equity; use portfolio value for sizing & loss cap |
| `data/atos.db` is read-only for SEO | WAL journal files owned by user `Kashif` (agent #2) | **Run `fix_permissions.bat` as Administrator** — then rename `atos_live.db` → `atos.db` |
| `data/atos.db-wal` + `data/atos.db-shm` locked | Created by Kashif's server session | Same — admin fix then delete WAL files |
| Saxo token **EXPIRED** | Last used >24h ago | Run `py -3 saxo_auth_auto.py` before any trading |
| ATOS universe tickers not mapped to Saxo UICs | `lookup_instruments.py` never run for new tickers | Run `py -3 lookup_instruments.py` |
| `atos_runner.py` never completed a full cycle | No daily run has happened yet | Fix bug #5 + auth first, then run `py -3 -X utf8 run_atos.py` |

### ✅ WORKAROUND IN PLACE
`atos_live.db` = fresh database created by agent #3, owned by SEO, contains:
- Starting equity: 10,000 SEK (2026-08-04)
- Initial weights: all 1.0
- 4 open positions synced from Saxo SIM

All code (`atos/database.py`, `atos_server.py`) now points to `atos_live.db`.

---

## 4. The 4 Open Positions (Bought 2026-08-03 by Agent #2)

| Ticker | Name | Shares | Entry Price | Currency | P&L (EUR) | Market |
|---|---|---|---|---|---|---|
| `PRX.AS` | Proximus | 1 | 41.24 | EUR | -0.37 | EU_OTHER |
| `NIBE-B.ST` | NIBE Industrier | 26 | 38.92 | SEK | -3.12 | OMX30 |
| `HEXA-B.ST` | Hexagon AB | 11 | 96.42 | SEK | -7.92 | OMX30 |
| `HM-B.ST` | H&M | 12 | 177.20 | SEK | +7.20 | OMX30 |

**Total invested: ~4,673 SEK** (47% of 10,000 SEK capital). **Unrealized P&L: ≈ -8.10 SEK** (-0.081%).

⚠️ These were placed by agent #2 **manually** on Saxo SIM — **NOT by the ATOS decision engine**. They have zero detector scores, zero algorithmic basis, and **no stop-loss orders set**.

---

## 5. Windows User Account Situation ⚠️ CRITICAL

Three Windows user accounts on this machine:
- **`SEO`** — original project owner. Owns all `atos/` files and `atos_runner.py`.
- **`Kashif`** — agent #2's session. Owns `atos_dashboard.py`, `run_atos.py`, `saxo_auth_auto.py`, `fix_permissions.bat`, and the WAL journal files.
- **`Kwaseem`** — agent #4's session. Can read all files but cannot modify SEO-owned files without admin permission fix.

**Files created by you (the agent) are owned by whichever user ran the terminal.**

**The permanent fix (run once):**
```
Right-click fix_permissions.bat → Run as Administrator
```
This grants all users full access to all files. Do this before editing anything owned by another user.

**Until fixed:** Create new files rather than editing files owned by another user.

---

## 6. How to Run — Start Here Every Session

### Step 1 — Pull latest code
```powershell
cd E:\saxobackup\SaxoTrader\files
git pull origin main
```

### Step 2 — Start the dashboard (keep this terminal open)
```powershell
py -3 -X utf8 atos_server.py
```
Open **http://localhost:8070** in browser.

### Step 3 — Refresh Saxo token (if expired, ~24h lifetime)
```powershell
py -3 saxo_auth_auto.py
```
Browser opens → log into Saxo SIM → tokens saved automatically.

### Step 4 — Run the daily trading cycle
```powershell
py -3 -X utf8 run_atos.py
```
Downloads market data → scores 71 tickers → places orders → updates DB → refreshes dashboard.

### Emergency stop
```powershell
New-Item -Path "E:\saxobackup\SaxoTrader\files\STOP_TRADING" -ItemType File
# Resume: Remove-Item "E:\saxobackup\SaxoTrader\files\STOP_TRADING"
```

### Sync Saxo positions to dashboard (if positions are missing)
```powershell
py -3 -X utf8 sync_saxo_positions.py
```

### End of session — ALWAYS push
```powershell
git add -A
git commit -m "agent: <describe what you did>"
git push origin main
```

---

## 7. File Map — What Everything Does

### Core ATOS Engine (owner: SEO)
| File | Purpose |
|---|---|
| `atos/universe.py` | 71 instruments, 5 market groups, detector overrides |
| `atos/features.py` | Technical indicators: EMA, ATR, ADX, RSI, MACD, Bollinger, Donchian |
| `atos/detectors.py` | D1-D5 signal detectors, score -100 to +100 each |
| `atos/decision_engine.py` | Combines detector scores → BUY/EXIT/HOLD |
| `atos/learner.py` | Updates detector weights after closed trades |
| `atos/risk.py` | All risk gates + ATR-based position sizing ⚠️ **HAS BUG #5** |
| `atos/database.py` | SQLite CRUD — now points to `data/atos_live.db` |
| `atos/dashboard_gen.py` | Legacy static HTML generator (not used with server) |
| `atos_runner.py` | Main daily orchestrator — `run_cycle()` |

### Dashboard & Server (mixed ownership)
| File | Owner | Purpose |
|---|---|---|
| `atos_server.py` | SEO | **USE THIS** — ThreadingHTTPServer, serves http://localhost:8070, reads `atos_live.db` |
| `atos_dashboard.py` | Kashif | Original server (single-threaded, buggy — do not use) |
| `run_atos.py` | Kashif | Wrapper: token check + atos_runner + skip FTP |

### Auth & Connectivity (owner: mixed)
| File | Owner | Purpose |
|---|---|---|
| `saxo_auth_auto.py` | Kashif | Auto OAuth — catches redirect on port 8071 |
| `saxo_auth.py` | SEO | Manual OAuth fallback |
| `saxo_token.json` | Local | OAuth token — **gitignored, never commit** |
| `saxo_client.py` | SEO | All Saxo API calls |

### Utilities (owner: SEO)
| File | Purpose |
|---|---|
| `sync_saxo_positions.py` | Sync live Saxo positions → `atos_live.db` |
| `create_fresh_db.py` | Create fresh `atos_live.db` from scratch + import positions |
| `lookup_instruments.py` | Map ATOS universe tickers to Saxo UICs |
| `test_atos_signal.py` | Test detector scores without placing orders |
| `fix_permissions.bat` | **Admin only** — fix file ownership for all users |

### Data Files
| File | Purpose |
|---|---|
| `data/atos_live.db` | **ACTIVE DB** — SEO-owned, writable, 4 positions |
| `data/atos.db` | Old DB — Kashif-owned WAL lock, **do not use until permissions fixed** |
| `data/instrument_map.csv` | Yahoo ticker → Saxo UIC mapping (117 entries, more needed) |
| `data/atos_risk_state.json` | Local risk capital tracker |
| `config/deploy.json` | FTP credentials — gitignored, **no longer used** |

---

## 8. Decision Engine — Scoring Thresholds

```
BUY  if combined score ≥ 55
EXIT if combined score ≤ 20 (open positions only)

D1 Trend       (EMA/ADX)       max +90  — confirms price direction
D2 Momentum    (RSI/MACD)      max +80  — confirms buying pressure
D3 Breakout    (Donchian 20d)  max +80  — new highs = strong signal
D4 MeanRevert  (Bollinger)     max +70  — disabled for Forex/Commodities
D5 Volume      (vol ratio)     max +50  — institutional interest

Weights: start all 1.0, learn after 10+ closed trades
Bounds: 0.30 min, 2.50 max
```

### Score Combination Formula
```
combined_score = sum(detector_score[i] × weight[i]) / sum(weight[i])
```
Weighted average, clamped to [-100, +100].

### Agent #4 Audit — Engine Rating: 5/10
| Aspect | Rating | Notes |
|---|---|---|
| Architecture | 8/10 | Solid multi-detector weighted scoring design |
| Intelligence | 5/10 | Basic step-function signals, no ML, hardcoded thresholds |
| Risk Management | 7/10 | Good gates (except Bug #5) — ATR sizing, market limits, kill switch |
| Self-Learning | 4/10 | Too simplistic — fixed ±0.05 step, ignores trade magnitude |
| Execution | 1/10 | **Has never run a single daily cycle** |

### Missing for "Super Smart" Status
- Regime detection (bull/bear/sideways market classifier)
- Trailing stop losses
- Position correlation / sector concentration checks
- Magnitude-aware learner
- VWAP integration
- Intraday signals
- Short selling logic

---

## 9. Risk Rules (Hard-Coded)

```
Capital:         10,000 SEK paper money
Risk per trade:  1% of capital, ATR-based position size
Stop loss:       Entry − 2.5 × ATR(14)
Max positions:   10 total (US=4, OMX30=2, DAX=2, Commodities=2, Forex=2)
Daily loss cap:  3% — no new entries if down >3% today
Commission:      0.08% per trade, min 1 USD
```

---

## 10. All Bugs Fixed — Do NOT Re-Introduce

### Bug #1 — D4 penalized trending breakouts ✅ FIXED (commit 7c2dfb8)
D4 now returns 0 (neutral) instead of -60 when stock is in uptrend (EMA20 > EMA50) and above upper Bollinger Band.

### Bug #2 — Orders sized from Saxo's €100k balance ✅ FIXED (commit 2f52c30)
Risk capital now anchored to `STARTING_CAPITAL_SEK = 10_000` in `atos/risk.py`.

### Bug #3 — Windows Unicode errors ✅ FIXED
Always use `py -3 -X utf8 script.py`.

### Bug #4 — Dashboard shows all "---" values ✅ FIXED (agent #3)
**Root cause chain:**
1. `atos_dashboard.py` used single-threaded `HTTPServer` — browser's `Promise.all()` fires 6 parallel API calls, all but one were dropped.
2. Two server instances running simultaneously (started by SEO and Kashif sessions) fighting on port 8070.
3. `data/atos.db` WAL journal files owned by Kashif — SEO session can't write → DB read-only.
4. DB was empty anyway (no daily cycle had run).

**Fix:** `atos_server.py` uses `ThreadingHTTPServer` + `SO_REUSEADDR`. Created `atos_live.db` as SEO-owned writable DB. Seeded with 10,000 SEK starting equity + 4 open positions from Saxo SIM.

### Bug #5 — risk.py equity/cash conflation 🔴 OPEN (found by Agent #4 audit)
**Root cause:** `risk_capital_sek` is used as both "available cash" and "total equity".
- `record_fill(-cost_sek)` subtracts full position cost from `risk_capital_sek`
- `calculate_position_size()` uses this same variable → position sizing shrinks after each buy
- `daily_loss_cap_breached()` compares `day_start_equity` vs `risk_capital_sek` → **false-triggers** the 3% circuit breaker after buying 2-3 positions (buying = cash drops = looks like a loss)
- `atos_runner.py` logs `total_equity = get_risk_capital()` → equity curve ignores open position values

**Impact:** If the engine runs, it would buy 2-3 positions then block all further trading for the day. Equity chart would show phantom losses.

**Required fix:** Separate cash tracking from portfolio equity. Use `cash + sum(open_position_values)` for equity, sizing, and loss cap calculations.

---

## 11. OAuth / Authentication

### Method A — Auto (recommended)
```powershell
py -3 saxo_auth_auto.py
```
Opens browser → Saxo SIM login → catches redirect on `http://localhost:8071/redirect` → saves `saxo_token.json`.

**One-time setup:** Register `http://localhost:8071/redirect` in Saxo dev portal:
→ https://developer.saxobank.com → Your App → Edit → Add Redirect URL

### Method B — Manual (fallback if A fails)
```powershell
py -3 saxo_auth.py
```
Opens browser → copy redirect URL back to terminal.
Redirect URI: `https://localhost/redirect` (already registered).

**Token expires every ~24 hours.**

---

## 12. Priority Task List for Next Agent

> **Work these in order. Mark done ✅ and push README before ending session.**

- [ ] **P0 — FIX BUG #5: risk.py equity/cash conflation** 🔴 BLOCKER
  Must fix before running first cycle. See §10 Bug #5 for details.
  In `atos/risk.py`:
  - Separate `available_cash` from `total_equity`
  - Position sizing should use `total_equity` (cash + open positions value)
  - Daily loss cap should compare equity snapshots, not cash
  - `atos_runner.py` equity logging should include open position values

- [ ] **P1 — Fix permissions** (ADMIN needed)
  ```
  Right-click fix_permissions.bat → Run as Administrator
  ```
  Then in PowerShell:
  ```powershell
  Copy-Item data\atos_live.db data\atos_new.db
  Remove-Item data\atos.db, data\atos.db-wal, data\atos.db-shm
  Rename-Item data\atos_new.db data\atos.db
  # Then update DB_PATH in atos/database.py and atos_server.py back to atos.db
  ```

- [ ] **P2 — Register OAuth redirect URI**
  Add `http://localhost:8071/redirect` in Saxo developer portal.
  Then test: `py -3 saxo_auth_auto.py`

- [ ] **P3 — Refresh expired Saxo token**
  ```powershell
  py -3 saxo_auth_auto.py
  ```

- [ ] **P4 — Map ATOS universe to Saxo UICs**
  ```powershell
  py -3 lookup_instruments.py
  ```
  Check missing: GLD, USO, Forex pairs not yet mapped. Bot signals but skips orders for these.

- [ ] **P5 — Run first full daily cycle**
  ```powershell
  py -3 -X utf8 run_atos.py
  ```
  This will: download data → score 71 tickers → attempt orders → update DB → dashboard refreshes.

- [ ] **P6 — Set up Task Scheduler** (ADMIN needed)
  See §13 below. Runs cycle automatically every day at 23:00.

- [ ] **P7 — Upgrade Decision Engine to "Super Smart"** (ATOS v2 roadmap)
  Agent #4 audit rated the engine 5/10. Key upgrades needed:
  - Regime detection (bull/bear/sideways classifier)
  - Trailing stop losses (not just static ATR stops)
  - Position correlation / sector concentration checks
  - Magnitude-aware learner (weight adjustments proportional to P&L size)
  - VWAP integration in D2 Momentum detector

---

## 13. Task Scheduler Setup (Admin PowerShell — one time)

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

---

## 14. Market Universe

```
71 instruments total across 5 groups:
  US Equities (35)   — AAPL, MSFT, NVDA, AMZN, META... max 4 positions
  OMX30 (15)         — Swedish blue chips              max 2 positions
  DAX40 (10)         — German blue chips               max 2 positions
  Commodities (4)    — GLD, SLV, USO, GDX              max 2 positions
  Forex (3)          — EURUSD=X, GBPUSD=X, USDJPY=X   max 2 positions

Detector overrides:
  Forex:       D4 MeanReversion DISABLED, Trend weight ×1.3
  Commodities: D4 MeanReversion DISABLED, Breakout weight ×1.3
```

---

## 15. Environment

```
OS:       Windows 11 (Lenovo ThinkPad)
Python:   3.14 (py -3 or python both work; always add -X utf8)
Users:    SEO (original), Kashif (agent #2), Kwaseem (agent #4)
Git:      Configured, pushing to GitHub
Terminal: Use PowerShell
```

---

## 16. Git Commit History

```
052ff20  feat: localhost dashboard v2, agent#2 files, full README rewrite
5b3e519  docs: comprehensive agent handover README
7c2dfb8  fix: D4 MeanReversion no longer penalizes trending breakouts
06ffbc9  feat: ATOS v1 — multi-market self-learning algo trading system
de8781b  Add ManualOrder field to order payload
a72e939  Document live-sizing bug fixes
2f52c30  Fix live sizing: anchor to STARTING_CAPITAL
ac35a61  Add read-only strategy dashboard
```

---

## 17. Agent Session Log

| Session | Date | User | Key Work Done |
|---|---|---|---|
| Agent #1 | 2026-08-03 | SEO | Built ATOS v1: universe, features, 5 detectors, decision engine, learner, risk engine, DB, runner, README |
| Agent #2 | 2026-08-03/04 | Kashif | Added local dashboard server, auto-OAuth, run_atos.py wrapper, placed 4 test orders on Saxo SIM, fixed JS bugs |
| Agent #3 | 2026-08-04 | SEO | Fixed dashboard showing "---": diagnosed dual-server conflict, Kashif WAL lock; created `atos_server.py` (ThreadingHTTPServer), `atos_live.db` (fresh writable DB), synced 4 Saxo positions, multi-agent README protocol |
| Agent #4 | 2026-08-04 | Kwaseem | **Full system audit**: Confirmed 4 positions are manual (not algorithmic), engine never ran (`last_run_date: null`), found critical Bug #5 (risk.py equity/cash conflation), rated decision engine 5/10, documented all algorithms & scoring logic, identified 11 improvement gaps, created comprehensive audit report |

**Next agent: You are Agent #5. Read §12 for your task list. P0 (Bug #5 fix) is BLOCKING — must fix before first daily cycle.**

---

## 18. Roadmap

| Phase | Status | Description |
|---|---|---|
| Phase 1 | ✅ Done | EMA crossover backtest |
| Phase 2 | ✅ Done | Saxo SIM single-strategy live trading |
| **ATOS v1** | ⚠️ Code ready, never executed | Multi-market self-learning system, localhost dashboard, 4 manual positions. Bug #5 blocks first run. |
| ATOS v2 | 🔒 Future | VWAP in D2, regime detection, trailing stops, correlation checks, magnitude-aware learner |
| Phase 3 | 🔒 **Locked** | Live money — only after 40+ closed trades, win rate >50%, PF >1.5 |

---

## 19. Agent #4 Additional Audit Findings (2026-08-04 03:03 PKT)

### Order History Analysis
The 4 open positions were **NOT** placed manually through the Saxo UI. They were placed via the **legacy SMA crossover strategy** in `saxo_client.py`. The `live_order_log.csv` shows:
- **8 failed attempts** before 4 successful fills
- First attempts tried insane sizes (14,469 shares of H&M!) due to Bug #2 (�100k Saxo balance)
- All 4 orders filled in a 5-second window at 16:43 on 2026-08-03
- Buy reason logged as `SMA crossover signal` � NOT the ATOS 5-detector engine

### Critical State File Discrepancies Found
| File | Current Value | Should Be | Risk |
|---|---|---|---|
| `data/daily_state.json` | `day_start_equity: 1,000,000.0` | 10,000 | Position sizing would be 100� too large if engine uses this |
| `data/risk_capital.json` | `risk_capital: 5,347.04` | ~10,000 minus position costs | Confirms Bug #5 � capital already reduced by position costs |

### Learner Crash Risk (Bug #6)
The 4 imported positions have NULL detector scores in the database. When these trades close, `learner.py` will attempt to iterate over NULL scores and crash with a TypeError.
**Fix:** Add NULL-check guard in `learner.py` before weight adjustment loop.

### Actual Fill Prices (from `live_order_log.csv`)
| Ticker | README Price | Actual Fill | Difference |
|---|---|---|---|
| HM-B.ST | 177.20 | 177.40 | +0.20 |
| HEXA-B.ST | 96.42 | 96.36 | -0.06 |
| NIBE-B.ST | 38.92 | 38.85 | -0.07 |
| PRX.AS | 41.24 | 41.31 | +0.07 |
