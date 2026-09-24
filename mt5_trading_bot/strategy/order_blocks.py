from typing import List
import pandas as pd
from .state import OBLevel, StrategyState
from .candles import is_tapped

def create_order_block(state: StrategyState, df: pd.DataFrame, bar_index: int, is_bullish: bool):
    """
    Search up to 10 candles back for opposite candle and create Order Block (OB).
    Direct reproduction of Pine Script OB logic.
    """
    if len(df) < 2:
        return

    ob_off = -1
    for i in range(1, min(11, len(df))):
        row = df.iloc[-1 - i]
        c = float(row["close"])
        o = float(row["open"])
        if is_bullish and c < o:
            ob_off = i
            break
        elif not is_bullish and c > o:
            ob_off = i
            break

    if ob_off != -1:
        row = df.iloc[-1 - ob_off]
        ob_bar = bar_index - ob_off
        if is_bullish:
            ob_top = float(row["open"])
            ob_bot = float(row["low"])
        else:
            ob_top = float(row["high"])
            ob_bot = float(row["open"])

        if ob_top > ob_bot:
            ob = OBLevel(left=ob_bar, right=bar_index, top=ob_top, bot=ob_bot, bull=is_bullish, active=True, deleted=False)
            state.obLevels.append(ob)

def update_order_blocks(state: StrategyState, df: pd.DataFrame, bar_index: int,
                        show_ob: bool = False, ob_delete_on_tap: bool = True,
                        max_ob: int = 20, tap_source: str = "TapByWick"):
    """
    Update existing OBs and handle tap deletion.
    """
    if not show_ob or len(df) == 0:
        return

    curr = df.iloc[-1]
    low_c = float(curr["low"])
    high_c = float(curr["high"])
    close_c = float(curr["close"])

    for ob in state.obLevels:
        if ob.deleted:
            continue
        ob.right = bar_index
        if ob_delete_on_tap and bar_index > ob.left:
            tapped = is_tapped(close_c, high_c, low_c, ob.top, ob.bot, tap_source)
            if tapped:
                ob.active = False
                ob.deleted = True

    # Trim max OB
    kept = 0
    for i in range(len(state.obLevels) - 1, -1, -1):
        ob = state.obLevels[i]
        if ob.deleted:
            continue
        kept += 1
        if kept > max_ob:
            ob.deleted = True
            ob.active = False

    # Compact deleted
    i = len(state.obLevels) - 1
    while i >= 0:
        if state.obLevels[i].deleted:
            state.obLevels.pop(i)
        i -= 1
