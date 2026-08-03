"""
fx.py
-----
The Saxo SIM account here is denominated in EUR, but every OMX30
instrument trades in SEK. Position sizing and cash checks need both
figures in the SAME currency, or they're silently wrong (comparing an EUR
balance against a SEK-priced stock as if they were equal is roughly an 11x
error, not a rounding difference).

This fetches the EUR/SEK rate via yfinance (same data source already used
elsewhere in this project) so account currency figures can be converted
into SEK before being used for sizing/cash checks against SEK instruments.
"""

import yfinance as yf

FALLBACK_EURSEK = 11.0  # rough fallback ONLY if the live fetch fails — log
                          # loudly when this is used, don't trust it silently


def get_eur_sek_rate() -> float:
    try:
        fast = yf.Ticker("EURSEK=X").fast_info
        rate = float(fast["last_price"])
        if rate <= 0:
            raise ValueError(f"Implausible EURSEK rate: {rate}")
        return rate
    except Exception as e:
        print(f"  [WARN] Could not fetch live EUR/SEK rate ({e}). "
              f"Using fallback {FALLBACK_EURSEK} — VERIFY this is close to "
              f"reality before trusting position sizing this cycle.")
        return FALLBACK_EURSEK
