from typing import List
import pandas as pd
from .state import FVGLevel, StrategyState
from .candles import is_tapped

def update_fvg(state: StrategyState, df: pd.DataFrame, bar_index: int,
               show_fvg: bool = False, fvg_delete_on_tap: bool = True,
               max_fvg: int = 30, tap_source: str = "TapByWick"):
    """
    Detect Fair Value Gaps (FVG) and handle deletion on tap.
    Direct reproduction of Pine Script SMC FVG section.
    """
    if not show_fvg or len(df) < 3:
        return

    curr = df.iloc[-1]
    prev2 = df.iloc[-3]

    low_c = float(curr["low"])
    high_c = float(curr["high"])
    close_c = float(curr["close"])
    high_2 = float(prev2["high"])
    low_2 = float(prev2["low"])

    # Update existing FVGs
    for fv in state.fvgLevels:
        if fv.deleted:
            continue
        fv.right = bar_index
        if fvg_delete_on_tap and bar_index > fv.left:
            tapped = is_tapped(close_c, high_c, low_c, fv.top, fv.bot, tap_source)
            if tapped:
                fv.active = False
                fv.deleted = True

    # Detect new Bullish FVG
    if low_c > high_2:
        fvg_top = low_c
        fvg_bot = high_2
        if fvg_top > fvg_bot:
            fv = FVGLevel(left=bar_index - 2, right=bar_index, top=fvg_top, bot=fvg_bot, bull=True, active=True, deleted=False)
            state.fvgLevels.append(fv)

    # Detect new Bearish FVG
    if high_c < low_2:
        fvg_top = low_2
        fvg_bot = high_c
        if fvg_top > fvg_bot:
            fv = FVGLevel(left=bar_index - 2, right=bar_index, top=fvg_top, bot=fvg_bot, bull=False, active=True, deleted=False)
            state.fvgLevels.append(fv)

    # Trim max FVG
    kept = 0
    for i in range(len(state.fvgLevels) - 1, -1, -1):
        fv = state.fvgLevels[i]
        if fv.deleted:
            continue
        kept += 1
        if kept > max_fvg:
            fv.deleted = True
            fv.active = False

    # Compact deleted
    i = len(state.fvgLevels) - 1
    while i >= 0:
        if state.fvgLevels[i].deleted:
            state.fvgLevels.pop(i)
        i -= 1
