# Algorithmic Trading Operating System (ATOS) v1
## Saxo Bank SIM — Paper Trading on OMX30, NASDAQ100, S&P500, DAX40, Gold, Oil & Forex

> **This is SIM / paper money only.** All orders go to Saxo's simulation gateway.
> No real money is at risk until you deliberately move to Phase 3 (see Roadmap below).

---

## What This System Does

ATOS is a **multi-market daily algo trading system** that:

- Scans **~80 instruments** across 7 markets every day
- Uses a **Decision Engine** with 5 signal detectors to score every ticker
- Places trades automatically on **Saxo SIM** (paper money)
- **Learns from every closed trade** — detector weights adapt over time
- Generates a **live HTML dashboard** at [namazic.com/atos](https://namazic.com/atos/) each morning
- Logs everything permanently to a **SQLite database** (`data/atos.db`)

---

## The 7 Markets (Ranked by Historical Algo Profitability)

| Tier | Market | Tickers | Why Included |
|---|---|---|---|
| 🥇 Core | **US Equities** (S&P500 + NASDAQ100) | ~35 | Highest Sharpe, best trend-following market |
| 🥇 Core | **Gold + Commodities** (GLD, SLV, USO, GDX) | 4 | Non-correlated, trends for months |
| 🥈 Strong | **DAX40** (Germany) | 10 | Europe's most liquid, good trends |
| 🥈 Strong | **OMX30** (Sweden) | 15 | Home market, good liquidity |
| 🥉 Diversifier | **Forex** (EUR/USD, GBP/USD, USD/JPY) | 3 | Counter-equity, trends on rate differentials |

---

## The Decision Engine

For every ticker, every day, ATOS runs **5 signal detectors** and combines them into a score:

```
Score = Weighted Average of 5 Detectors  (-100 to +100)

  Detector 1 — Trend       EMA 20/50/200 alignment + ADX strength
  Detector 2 — Momentum    RSI crossing 50 + MACD direction
  Detector 3 — Breakout    Donchian Channel (Turtle Trader method)
  Detector 4 — Mean Revert Bollinger Band extremes + RSI oversold
  Detector 5 — Volume      Relative volume vs 20-day average

  Score ≥ 55  →  BUY signal
  Score ≤ 20  →  EXIT signal (on open position)
```

### Self-Learning Weights

The system starts with **equal weights** for all 5 detectors. After every closed trade:

- **Profitable trade** → detectors that said BUY get rewarded (+0.06)
- **Loss trade** → detectors that warned us get rewarded; those that said BUY get penalised (-0.04)
- Weights are normalized after every update, bounded between 0.30 and 2.50

Over hundreds of trades, the best predictors for *your specific markets* earn more influence automatically.

---

## Risk Rules (Hard — Never Bypassed)

| Rule | Value |
|---|---|
| Risk per trade | 1% of risk capital (ATR-based) |
| Stop loss | Entry − 2.5 × ATR |
| Max open positions | 10 total (4 US, 2 OMX30, 2 DAX, 2 Commodities, 2 Forex) |
| Daily loss cap | No new entries if ATOS equity down ≥ 3% today |
| Kill switch | Create file named `STOP_TRADING` to halt everything |
| Min signal score | 55/100 — weak signals are never traded |

---

## How to Run

### First time setup (one-time)
```powershell
pip install -r requirements.txt
python saxo_auth.py          # login to Saxo SIM (PKCE OAuth)
python lookup_instruments.py # build Saxo UIC map for OMX30/DAX stocks
```

### Daily run (schedule this with Windows Task Scheduler)
```powershell
python atos_runner.py
```

### Schedule it (recommended: run once per day after market close, e.g. 23:00 PKT)
- Open **Task Scheduler** → Create Basic Task
- Trigger: Daily at 23:00
- Action: `python C:\path\to\atos_runner.py`
- Start in: `C:\path\to\your\project\`

### View dashboard
After each run, open: **[https://namazic.com/atos/](https://namazic.com/atos/)**
Or locally: `dashboard/index.html`

---

## Project Structure

```
algo-platform/
│
├── atos/                         ← ATOS core (new)
│   ├── universe.py               ← 7-market instrument universe
│   ├── features.py               ← All indicator calculations
│   ├── detectors.py              ← 5 signal detectors
│   ├── decision_engine.py        ← Weighted score combiner
│   ├── learner.py                ← Adaptive weight updater
│   ├── risk.py                   ← Risk engine + position sizing
│   ├── database.py               ← SQLite database layer
│   └── dashboard_gen.py          ← HTML dashboard generator
│
├── atos_runner.py                ← Daily entry point (run this)
│
├── config/
│   └── deploy.json               ← FTP credentials (gitignored)
│
├── data/
│   ├── atos.db                   ← SQLite: all trades, weights, equity
│   └── atos_risk_state.json      ← Daily capital tracker
│
├── dashboard/
│   └── index.html                ← Generated dashboard (uploaded to namazic.com)
│
│ ── ORIGINAL FILES (Phase 1 + 2 — unchanged) ───────────────────────
├── config.py                     ← Original strategy settings
├── strategy.py                   ← EMA crossover strategy
├── backtest.py                   ← Backtesting engine
├── backtest_cfd.py               ← CFD backtesting
├── saxo_auth.py                  ← Saxo PKCE OAuth (shared)
├── saxo_client.py                ← Saxo API client (shared)
├── saxo_live_engine.py           ← Original single-strategy live engine
├── saxo_live_main.py             ← Original entry point
├── kill_switch.py                ← Original kill switch
├── fx.py                         ← FX conversion (shared)
├── instrument_map.py             ← Saxo UIC mapping (shared)
├── data_loader.py                ← Historical data (backtest)
└── live_data.py                  ← Live data fetcher (backtest)
```

---

## Dashboard (Live at namazic.com/atos)

The HTML dashboard is generated fresh every morning and automatically uploaded to your domain. It shows:

- **Total equity** and today's P&L
- **Algorithm weights** with progress bars (watch them evolve over time)
- **Weight evolution chart** — see the learning happen visually
- **Today's trades** (BUY / EXIT / BLOCKED with reasons)
- **Open positions** with entry price, stop loss, entry date
- **90-day equity curve** chart

No server required — it's a self-contained HTML file with all data baked in.

---

## Roadmap

| Phase | Status | Description |
|---|---|---|
| **Phase 1** | ✅ Done | EMA crossover backtest on OMX30 |
| **Phase 2** | ✅ Done | Saxo SIM live paper trading (single strategy) |
| **ATOS v1** | 🔨 **Now** | Multi-strategy, self-learning, 7 markets, dashboard |
| **Phase 3** | 🔒 Locked | Live trading — only after 4+ weeks of stable ATOS paper results |

> **Phase 3 rule:** Never switch to live money based on ATOS looking good in the code. Switch only after reading `data/atos.db` trade history critically — consistent positive performance over weeks with realistic fills and no large blocked orders.

---

## Change Log

### Aug 2026 — ATOS v1 launched

**New system built on top of Phase 1/2 infrastructure:**

- `atos/` package: universe (7 markets), features, 5 detectors, decision engine, learner, risk engine, SQLite database, HTML dashboard generator
- `atos_runner.py`: daily orchestrator replacing single-strategy `saxo_live_engine.py`
- `config/deploy.json`: FTP credentials for auto-upload to namazic.com/atos
- `dashboard/index.html`: dark-theme dashboard with Chart.js equity curve + weight evolution

**Markets added vs. Phase 2:** S&P500 top 50, DAX40, Gold (GLD), Silver (SLV), WTI Oil (USO), Gold Miners (GDX), EUR/USD, GBP/USD, USD/JPY

**Files untouched from Phase 1/2:** `saxo_auth.py`, `saxo_client.py`, `kill_switch.py`, `fx.py`, `instrument_map.py`, `strategy.py`, `backtest.py`, `config.py`

---

### Aug 2026 (Phase 2) — Fixed oversized/rejected live BUY orders

*(details preserved below)*

**Symptom:** `saxo_live_engine.py` was placing BUY orders worth millions of SEK that Saxo's SIM API rejected with `400 Bad Request`.

**Root causes fixed:**
1. Position sizing used live Saxo account equity instead of `config.STARTING_CAPITAL`
2. No per-instrument currency conversion (EUR/USD prices compared against SEK cash)
3. Saxo SIM is EUR-denominated; real account is SEK — two separate accounts
4. Order failures logged without Saxo's actual rejection reason
5. `ManualOrder` field missing from order payload (Saxo requirement)

**Files touched:** `fx.py`, `instrument_map.py`, `kill_switch.py`, `saxo_client.py`, `saxo_live_engine.py`

---

## Security Notes

- `config/deploy.json` contains FTP credentials — **never commit this file**
- `saxo_token.json` contains Saxo session tokens — **never commit or share**
- Both are gitignored. If you ever accidentally commit them, rotate credentials immediately.
- The trading bot runs locally on your Windows machine only — no credentials leave your machine.
