"""
atos/decision_engine.py
------------------------
Combines the 8 detector scores into a single buy/sell decision.

The engine:
  1. Loads current weights from the database
  2. Runs all 8 detectors on the feature row
  3. Computes a weighted average score
  4. Returns BUY / HOLD / EXIT with the score breakdown

Weights are learned over time by learner.py — this module only reads them.
"""

import pandas as pd
from typing import NamedTuple

from .detectors import (
    Detector1_Trend, Detector2_Momentum, Detector3_Breakout,
    Detector4_MeanReversion, Detector5_Volume,
    Detector6_SmartMoney, Detector7_MomentumQuality, Detector8_Regime,
)
from .universe import DETECTOR_MARKET_OVERRIDES
from . import database as db


# Adaptive thresholds — adjust based on market regime
REGIME_THRESHOLDS = {
    'BULL':       {'buy': 45, 'exit': 15},  # Easier entry, hold longer
    'SIDEWAYS':   {'buy': 60, 'exit': 25},  # Harder entry, exit faster
    'BEAR':       {'buy': 70, 'exit': 30},  # Very strict entry, quick exit
    'TRANSITION': {'buy': 55, 'exit': 20},  # Default thresholds
}


class Decision(NamedTuple):
    action:         str     # 'BUY' | 'EXIT' | 'HOLD'
    score:          float   # combined weighted score (-100 to 100)
    regime:         str     # 'BULL' | 'BEAR' | 'SIDEWAYS' | 'TRANSITION'
    d1_trend:       float
    d2_momentum:    float
    d3_breakout:    float
    d4_mean_revert: float
    d5_volume:      float
    d6_smart_money: float
    d7_mom_quality: float
    d8_regime:      float
    trailing_stop:  float   # calculated trailing stop price (0 if N/A)


_d1 = Detector1_Trend()
_d2 = Detector2_Momentum()
_d3 = Detector3_Breakout()
_d4 = Detector4_MeanReversion()
_d5 = Detector5_Volume()
_d6 = Detector6_SmartMoney()
_d7 = Detector7_MomentumQuality()
_d8 = Detector8_Regime()


def evaluate(row: pd.Series, market_group: str,
             weights: dict | None = None,
             is_open_position: bool = False) -> Decision:
    """
    Evaluate a single ticker's latest feature row.

    Parameters
    ----------
    row             : last row of features DataFrame (from features.add_all)
    market_group    : e.g. "US Equities", "Forex", "Commodities"
    weights         : dict of detector weights (if None, loaded from DB)
    is_open_position: True when checking exit for an already-open trade
    """
    # Load weights (now 8 detectors)
    if weights is None:
        weights = db.get_current_weights()
    
    # Per-asset-class overrides
    overrides = DETECTOR_MARKET_OVERRIDES.get(market_group, {})
    mr_enabled = overrides.get('mean_reversion_enabled', True)
    trend_boost = overrides.get('trend_weight_boost', 1.0)
    breakout_boost = overrides.get('breakout_weight_boost', 1.0)
    
    # Run all 8 detectors
    s1 = _d1.score(row)
    s2 = _d2.score(row)
    s3 = _d3.score(row)
    s4 = _d4.score(row, enabled=mr_enabled)
    s5 = _d5.score(row)
    s6 = _d6.score(row)  # Smart Money
    s7 = _d7.score(row)  # Momentum Quality
    s8 = _d8.score(row)  # Regime
    
    # Apply weights with boosts
    w1 = weights.get('w_trend', 1.0) * trend_boost
    w2 = weights.get('w_momentum', 1.0)
    w3 = weights.get('w_breakout', 1.0) * breakout_boost
    w4 = weights.get('w_mean_revert', 1.0) if mr_enabled else 0.0
    w5 = weights.get('w_volume', 1.0)
    w6 = weights.get('w_smart_money', 1.0)
    w7 = weights.get('w_mom_quality', 1.0)
    w8 = weights.get('w_regime', 1.0)
    
    total_weight = w1 + w2 + w3 + w4 + w5 + w6 + w7 + w8
    if total_weight == 0:
        combined = 0.0
    else:
        combined = (s1*w1 + s2*w2 + s3*w3 + s4*w4 + s5*w5 + 
                   s6*w6 + s7*w7 + s8*w8) / total_weight
    
    # Determine regime from the row
    regime = str(row.get('regime', 'TRANSITION'))
    if regime not in REGIME_THRESHOLDS:
        regime = 'TRANSITION'
    
    # Adaptive thresholds
    thresholds = REGIME_THRESHOLDS[regime]
    buy_threshold = thresholds['buy']
    exit_threshold = thresholds['exit']
    
    # Trailing stop calculation
    atr = row.get('atr', 0)
    trailing_stop = 0.0
    if pd.notna(atr) and atr > 0:
        trailing_stop = row.get('Close', 0.0) - 2.0 * atr
    
    # Determine action
    if is_open_position:
        action = 'EXIT' if combined <= exit_threshold else 'HOLD'
    else:
        action = 'BUY' if combined >= buy_threshold else 'HOLD'
    
    return Decision(
        action=action,
        score=round(combined, 1),
        regime=regime,
        d1_trend=round(s1, 1),
        d2_momentum=round(s2, 1),
        d3_breakout=round(s3, 1),
        d4_mean_revert=round(s4, 1),
        d5_volume=round(s5, 1),
        d6_smart_money=round(s6, 1),
        d7_mom_quality=round(s7, 1),
        d8_regime=round(s8, 1),
        trailing_stop=round(trailing_stop, 4),
    )


def scan_universe(universe_data: dict[str, pd.DataFrame],
                  market_group_fn,
                  open_tickers: set[str],
                  weights: dict | None = None) -> dict[str, Decision]:
    """
    Evaluate every ticker in universe_data.

    Returns
    -------
    dict mapping ticker → Decision for all tickers with a non-HOLD signal,
    plus all tickers that are currently open positions (for exit checking).
    """
    if weights is None:
        weights = db.get_current_weights()

    results = {}
    for ticker, df in universe_data.items():
        if df is None or df.empty or len(df) < 50:
            continue
        row = df.iloc[-1]
        if pd.isna(row.get("ema50")) or pd.isna(row.get("atr")):
            continue   # not enough history yet

        market_group  = market_group_fn(ticker)
        is_open       = ticker in open_tickers
        decision      = evaluate(row, market_group, weights, is_open_position=is_open)

        # Keep: BUY signals, EXIT signals, and all open positions
        if decision.action != "HOLD" or is_open:
            results[ticker] = decision

    return results
