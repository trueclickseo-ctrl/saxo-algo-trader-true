"""
atos/learner.py
----------------
Updates detector weights after every closed trade.

The core idea:
  - When a trade is PROFITABLE: reward detectors that were POSITIVE at entry
  - When a trade is a LOSS:     reward detectors that were NEGATIVE at entry
                                (they were trying to warn us)
  - After updating: normalize weights so they sum to 5.0 (one per detector)
  - Weights are bounded: min 0.3 (never fully ignored), max 2.5 (never dominant)

This is gradient-free reinforcement learning on real trade outcomes.
Over hundreds of trades, detectors that consistently predict correctly
earn more influence. Those that fire randomly lose influence.
"""

from . import database as db

# Learning rate — how much each trade shifts the weights
LEARN_RATE_REWARD  = 0.06   # reward correct detector
LEARN_RATE_PENALISE = 0.04  # penalise wrong detector

# Weight bounds — keep all detectors in the game
MIN_WEIGHT = 0.30
MAX_WEIGHT = 2.50

# Target sum of all weights (5 detectors × 1.0 = 5.0 at equal weights)
TARGET_SUM = 5.0

# Minimum trades before learning kicks in (avoid overreacting to early noise)
MIN_TRADES_TO_LEARN = 10


def update_weights_from_closed_trade(trade: dict) -> dict | None:
    """
    Given a single closed trade record from the DB, update detector weights.
    Returns new weights dict, or None if minimum trades threshold not met.

    trade dict keys used:
      was_profitable : 1 (profit) or 0 (loss)
      d1_trend, d2_momentum, d3_breakout, d4_mean_revert, d5_volume
        (these are the scores at ENTRY time — positive means detector said BUY)
    """
    current = db.get_current_weights()
    num_trades = current.get("num_trades", 0)

    if num_trades < MIN_TRADES_TO_LEARN:
        # Just increment count and return without changing weights
        db.save_weights(current, num_trades + 1,
                        note=f"warming up ({num_trades+1}/{MIN_TRADES_TO_LEARN})")
        return None

    profitable = bool(trade.get("was_profitable"))

    # Each detector's entry score — positive means it was bullish at entry
    detector_scores = {
        "w_trend":       trade.get("d1_trend", 0) or 0,
        "w_momentum":    trade.get("d2_momentum", 0) or 0,
        "w_breakout":    trade.get("d3_breakout", 0) or 0,
        "w_mean_revert": trade.get("d4_mean_revert", 0) or 0,
        "w_volume":      trade.get("d5_volume", 0) or 0,
    }

    new_weights = {}
    for key, current_w in current.items():
        if key in ("num_trades",):
            continue
        det_score = detector_scores.get(key, 0)

        if profitable:
            # Trade won: reward detectors that were bullish (positive score)
            if det_score > 0:
                new_w = current_w + LEARN_RATE_REWARD
            elif det_score < 0:
                new_w = current_w - LEARN_RATE_PENALISE   # was negative, trade won = wrong
            else:
                new_w = current_w   # neutral detector — no change
        else:
            # Trade lost: reward detectors that were bearish (negative score)
            if det_score < 0:
                new_w = current_w + LEARN_RATE_REWARD     # it warned us — reward
            elif det_score > 0:
                new_w = current_w - LEARN_RATE_PENALISE   # it said buy, we lost
            else:
                new_w = current_w

        # Apply bounds
        new_weights[key] = max(MIN_WEIGHT, min(MAX_WEIGHT, new_w))

    # Normalize so total = TARGET_SUM
    total = sum(new_weights.values())
    if total > 0:
        factor = TARGET_SUM / total
        new_weights = {k: round(v * factor, 4) for k, v in new_weights.items()}

    note = (f"trade #{num_trades+1} {'PROFIT' if profitable else 'LOSS'} — "
            f"{trade.get('ticker', '?')} @ {trade.get('exit_date', '?')}")
    db.save_weights(new_weights, num_trades + 1, note=note)
    return new_weights


def run_learning_pass():
    """
    Called once per daily run. Reviews all trades closed since the last
    weight update and applies learning for each.

    Returns summary of what changed.
    """
    before = db.get_current_weights()
    closed = db.get_recent_closed_trades(n=200)

    num_trades_before = before.get("num_trades", 0)
    new_trades = [t for t in closed
                  if t.get("was_profitable") is not None]

    # Only process trades that haven't been learned from yet
    # (simple heuristic: process trades beyond the current count)
    unprocessed = new_trades[num_trades_before:]

    if not unprocessed:
        return {"new_trades_processed": 0, "weights": before}

    for trade in unprocessed:
        update_weights_from_closed_trade(trade)

    after = db.get_current_weights()
    return {
        "new_trades_processed": len(unprocessed),
        "weights_before": before,
        "weights_after":  after,
    }


def format_weight_bar(weight: float, max_w: float = MAX_WEIGHT, width: int = 10) -> str:
    """Returns a simple ASCII bar for terminal display."""
    filled = round((weight / max_w) * width)
    return "█" * filled + "░" * (width - filled)
