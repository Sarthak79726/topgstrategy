from typing import Tuple

def candle_zone(o: float, c: float, h: float, l: float, is_high: bool, zone_body_pct: float = 1.0) -> Tuple[float, float]:
    """
    Calculate candle zone boundaries based on open, close, high, low, and zone body % padding.
    Direct reproduction of Pine Script f_candleZone().
    """
    body_top = max(o, c)
    body_bot = min(o, c)
    pad = max(body_top - body_bot, 0.0) * zone_body_pct * 0.01
    top_ = h if is_high else (body_bot + pad)
    bot_ = (body_top - pad) if is_high else l
    return top_, bot_

def is_tapped(r_close: float, r_high: float, r_low: float, top_: float, bot_: float, tap_source: str = "TapByWick") -> bool:
    """
    Check if candle taps zone boundaries.
    Direct reproduction of Pine Script f_isTapped().
    """
    if tap_source == "TapByClose":
        return r_close <= top_ and r_close >= bot_
    else:
        return r_high >= bot_ and r_low <= top_
