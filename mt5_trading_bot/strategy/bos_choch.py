from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from .state import StrategyState, Snap
from .structure import make_snap_current, make_snap_at_bar

@dataclass
class StructureEvent:
    type: str  # BULLISH_CHOCH, BEARISH_CHOCH, BULLISH_BOS, BEARISH_BOS, BULL_RETRACEMENT, BEAR_RETRACEMENT
    bar_index: int
    price: float
    dual_choch: bool = False
    details: Dict[str, Any] = None

def detect_structure_shifts(open_c: float, close_c: float, high_c: float, low_c: float,
                            open_p: float, close_p: float, high_p: float, low_p: float) -> Tuple[bool, bool]:
    """
    Detect bullish and bearish ISS candle shifts.
    bearishIssShift = redP and redC and close < low[1]
    bullishIssShift = greenP and greenC and close > high[1]
    """
    red_p = close_p < open_p
    green_p = close_p > open_p
    red_c = close_c < open_c
    green_c = close_c > open_c

    bearish_shift = red_p and red_c and (close_c < low_p)
    bullish_shift = green_p and green_c and (close_c > high_p)

    return bullish_shift, bearish_shift
