"""
atos/detectors.py
------------------
5 Signal Detectors — the core of the ATOS Decision Engine.

Each detector receives a feature row (last row of the computed DataFrame)
and returns a SCORE from -100 to +100:
  +100 = very strong buy signal
     0 = neutral / no opinion
  -100 = very strong sell / exit signal

Detectors NEVER place orders. They only score. The Decision Engine combines them.
"""

import pandas as pd
import numpy as np


class Detector1_Trend:
    """
    Trend Detector — EMA alignment + ADX strength.
    Best for: All markets in trending conditions.
    Theory: 20 > 50 > 200 EMA = confirmed uptrend. ADX > 25 = trend has momentum.
    """
    name = "trend"

    def score(self, row: pd.Series) -> float:
        score = 0.0

        # EMA hierarchy — the trend ladder
        if pd.notna(row.get("ema20")) and pd.notna(row.get("ema50")):
            if row["Close"] > row["ema20"]:
                score += 20   # price above fast MA
            if row["ema20"] > row["ema50"]:
                score += 25   # fast above slow = uptrend
            if pd.notna(row.get("ema200")) and row["ema50"] > row["ema200"]:
                score += 25   # slow above 200 = long-term bull
            if pd.notna(row.get("ema200")) and row["Close"] > row["ema200"]:
                score += 10   # price above 200 EMA = institutional support

        # ADX — trend strength confirmation
        if pd.notna(row.get("adx")):
            if row["adx"] > 30:
                score += 20   # strong trend
            elif row["adx"] > 20:
                score += 10   # moderate trend
            elif row["adx"] < 15:
                score -= 10   # trendless — penalise

        # Higher Highs / Higher Lows — market structure
        if row.get("higher_high") and row.get("higher_low"):
            score += 10
        elif row.get("lower_high") and row.get("lower_low"):
            score -= 20

        return float(max(-100, min(100, score)))


class Detector2_Momentum:
    """
    Momentum Detector — RSI + MACD.
    Best for: Equities in early-to-mid trend phase.
    Theory: RSI crossing 50 from below = momentum just flipped bullish.
            MACD histogram turning positive = acceleration.
    """
    name = "momentum"

    def score(self, row: pd.Series) -> float:
        score = 0.0

        if pd.notna(row.get("rsi")):
            rsi = row["rsi"]
            if row.get("rsi_cross_up50"):
                score += 40    # momentum just crossed — strongest signal
            elif 50 <= rsi <= 65:
                score += 25    # healthy momentum zone
            elif rsi > 65:
                score += 10    # still bullish but getting stretched
            elif rsi > 75:
                score -= 20    # overbought — exit risk
            elif rsi < 35:
                score += 20    # oversold bounce potential (with trend confirmation)
            elif rsi < 30:
                score += 30    # deeply oversold
            elif rsi < 50:
                score -= 10    # below momentum line

        if pd.notna(row.get("macd")) and pd.notna(row.get("macd_signal")):
            if row["macd"] > row["macd_signal"] and row["macd"] > 0:
                score += 30    # MACD above signal AND above zero = confirmed bull
            elif row["macd"] > row["macd_signal"]:
                score += 15    # MACD above signal but below zero = early
            elif row["macd"] < row["macd_signal"]:
                score -= 15    # bearish MACD

        return float(max(-100, min(100, score)))


class Detector3_Breakout:
    """
    Breakout Detector — Donchian Channel (Turtle Trader style).
    Best for: Commodities, high-volatility equities, trend starts.
    Theory: Breaking the 20-day high = institutional money entering.
            Used by the famous Turtle Traders with consistent success.
    """
    name = "breakout"

    def score(self, row: pd.Series) -> float:
        score = 0.0

        if pd.notna(row.get("donchian_high")) and pd.notna(row.get("donchian_low")):
            price_range = row["donchian_high"] - row["donchian_low"]
            if price_range > 0:
                # Position in range: 0 = at bottom, 1 = at top
                position = (row["Close"] - row["donchian_low"]) / price_range

                if row.get("donchian_breakout_up"):
                    score += 80    # NEW 20-day high — strongest breakout signal
                elif position > 0.85:
                    score += 40    # Near top of range — breakout approaching
                elif position > 0.60:
                    score += 15    # Upper half of range
                elif position < 0.15:
                    score -= 40    # Near 20-day low — avoid
                elif position < 0.40:
                    score -= 10    # Lower half — weak

            if row.get("donchian_breakout_down"):
                score -= 70        # Breaking 20-day low — strong exit signal

        return float(max(-100, min(100, score)))


class Detector4_MeanReversion:
    """
    Mean Reversion Detector — Bollinger Bands + RSI oversold.
    Best for: Equities in sideways markets.
    Theory: When price stretches too far from the mean (lower BB), it tends to snap back.
    WARNING: DISABLED for Forex and Commodities (they trend — don't fade them).
    """
    name = "mean_revert"

    def score(self, row: pd.Series, enabled: bool = True) -> float:
        if not enabled:
            return 0.0   # disabled for trending asset classes

        score = 0.0

        if pd.notna(row.get("bb_pct")) and pd.notna(row.get("rsi")):
            bb_pct = row["bb_pct"]  # 0=lower band, 1=upper band
            rsi    = row["rsi"]

            # Oversold reversal opportunity
            if bb_pct < 0.05 and rsi < 30:
                score += 70    # Price at/below lower band AND deeply oversold
            elif bb_pct < 0.15 and rsi < 40:
                score += 40    # Near lower band, moderately oversold
            elif bb_pct < 0.25 and rsi < 50:
                score += 20    # Below mid-band with weak momentum

            # Overbought — exit signal
            elif bb_pct > 0.95 and rsi > 70:
                score -= 60    # At upper band AND overbought — exit warning
            elif bb_pct > 0.80 and rsi > 65:
                score -= 30    # Approaching upper extreme

            # BB width — narrow band = volatility squeeze (breakout coming)
            if pd.notna(row.get("bb_width")) and row["bb_width"] < 0.02:
                score += 10    # Squeeze often precedes a strong move

        return float(max(-100, min(100, score)))


class Detector5_Volume:
    """
    Volume Confirmation Detector.
    Best for: Equities (stocks have volume data). Neutral for Forex/Commodities.
    Theory: High volume on a breakout = institutional participation = more reliable.
            Low volume on a move = suspect — could reverse easily.
    """
    name = "volume"

    def score(self, row: pd.Series) -> float:
        # No volume data (Forex, some ETFs) — return neutral
        if not row.get("has_volume", True):
            return 0.0
        if pd.isna(row.get("vol_ratio")):
            return 0.0

        vol_ratio = row["vol_ratio"]
        score = 0.0

        if vol_ratio >= 2.0:
            score += 50    # Very high volume — strong institutional interest
        elif vol_ratio >= 1.5:
            score += 30    # Above-average volume — good confirmation
        elif vol_ratio >= 1.1:
            score += 15    # Slightly above average
        elif vol_ratio < 0.7:
            score -= 20    # Low volume — weak conviction, possible fade
        elif vol_ratio < 0.5:
            score -= 35    # Very low volume — don't trust the move

        return float(max(-100, min(100, score)))


# ── Convenience: all 5 detectors ──────────────────────────────────
ALL_DETECTORS = [
    Detector1_Trend(),
    Detector2_Momentum(),
    Detector3_Breakout(),
    Detector4_MeanReversion(),
    Detector5_Volume(),
]
