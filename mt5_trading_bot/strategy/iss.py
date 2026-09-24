from typing import Optional, Dict, Any
import pandas as pd
from .state import StrategyState, Level
from .candles import candle_zone
from .levels import add_level_from_bar_ready
from .structure import make_snap_at_bar, make_snap_current

def reset_bull_iss(state: StrategyState):
    """Reset all Bullish ISS state variables to initial state."""
    state.bullIssState = 0
    state.bullIssBaseConfirmed = False
    state.bullIssBaseLow = None
    state.bullIssBaseLowBar = None
    state.bullIssRunHigh = None
    state.bullIssRunHighBar = None
    state.bullIss1Level = None
    state.bullIss1Bar = None
    state.bullIss2Level = None
    state.bullIss2Bar = None
    state.bullIssAfterBreakRunHigh = None
    state.bullIssAfterBreakRunHighBar = None
    state.bullIssAfterBreakRunLow = None
    state.bullIssAfterBreakRunLowBar = None
    state.bullIssBosBars.clear()
    state.bullIssBosLvls.clear()

def reset_bear_iss(state: StrategyState):
    """Reset all Bearish ISS state variables to initial state."""
    state.bearIssState = 0
    state.bearIssBaseConfirmed = False
    state.bearIssBaseHigh = None
    state.bearIssBaseHighBar = None
    state.bearIssRunLow = None
    state.bearIssRunLowBar = None
    state.bearIss1Level = None
    state.bearIss1Bar = None
    state.bearIss2Level = None
    state.bearIss2Bar = None
    state.bearIssAfterBreakRunLow = None
    state.bearIssAfterBreakRunLowBar = None
    state.bearIssAfterBreakRunHigh = None
    state.bearIssAfterBreakRunHighBar = None
    state.bearIssBosBars.clear()
    state.bearIssBosLvls.clear()

def update_iss_state(state: StrategyState, bar_index: int, open_c: float, close_c: float, high_c: float, low_c: float,
                     bullish_shift: bool, bearish_shift: bool, df: pd.DataFrame,
                     enable_iss: bool = True, zone_body_pct: float = 1.0) -> Optional[str]:
    """
    Execute full 4-state ISS state machine for Bullish and Bearish ISS.
    Returns signal event string ("BULL_ISS4_CONFIRMED" / "BEAR_ISS4_CONFIRMED") if confirmed on current candle.
    """
    if not enable_iss:
        return None

    event_result = None

    # --- Bullish ISS Invalidation ---
    bull_invalidated = (state.bullIssState >= 2 and state.bullIssBaseLow is not None and close_c < state.bullIssBaseLow)
    if bull_invalidated:
        reset_bull_iss(state)

    # --- Bearish ISS Invalidation ---
    bear_invalidated = (state.bearIssState >= 2 and state.bearIssBaseHigh is not None and close_c > state.bearIssBaseHigh)
    if bear_invalidated:
        reset_bear_iss(state)

    # --- Bullish ISS State Machine ---
    if state.bullIssState == 1:
        if state.bullIssBaseLow is None or low_c < state.bullIssBaseLow:
            state.bullIssBaseLow = low_c
            state.bullIssBaseLowBar = bar_index
            state.bullIssRunHigh = high_c
            state.bullIssRunHighBar = bar_index
            state.bullIssBaseConfirmed = False
        if not state.bullIssBaseConfirmed:
            if bullish_shift:
                state.bullIssBaseConfirmed = True
                state.bullIssRunHigh = high_c
                state.bullIssRunHighBar = bar_index
        else:
            if state.bullIssRunHigh is None or high_c > state.bullIssRunHigh:
                state.bullIssRunHigh = high_c
                state.bullIssRunHighBar = bar_index
            if bearish_shift and state.bullIssRunHighBar is not None and state.bullIssRunHighBar < bar_index:
                state.bullIss1Level = state.bullIssRunHigh
                state.bullIss1Bar = state.bullIssRunHighBar
                state.bullIssState = 2
                state.bullIss2Level = low_c
                state.bullIss2Bar = bar_index

    elif state.bullIssState == 2:
        if state.bullIss2Level is not None and low_c < state.bullIss2Level:
            state.bullIss2Level = low_c
            state.bullIss2Bar = bar_index
        if state.bullIss1Level is not None and close_c > state.bullIss1Level:
            state.bullIssAfterBreakRunHigh = high_c
            state.bullIssAfterBreakRunHighBar = bar_index
            state.bullIssAfterBreakRunLow = low_c
            state.bullIssAfterBreakRunLowBar = bar_index
            state.bullIssState = 3

    elif state.bullIssState == 3:
        if state.bullIss2Level is not None and low_c < state.bullIss2Level:
            state.bullIss2Level = low_c
            state.bullIss2Bar = bar_index
        if state.bullIssAfterBreakRunHigh is None or high_c > state.bullIssAfterBreakRunHigh:
            state.bullIssAfterBreakRunHigh = high_c
            state.bullIssAfterBreakRunHighBar = bar_index
            state.bullIssAfterBreakRunLow = low_c
            state.bullIssAfterBreakRunLowBar = bar_index
        elif state.bullIssAfterBreakRunLow is None or low_c < state.bullIssAfterBreakRunLow:
            state.bullIssAfterBreakRunLow = low_c
            state.bullIssAfterBreakRunLowBar = bar_index

        if bearish_shift and state.bullIssAfterBreakRunHighBar is not None and state.bullIssAfterBreakRunLowBar is not None:
            state.bullIssState = 4

    elif state.bullIssState == 4:
        if state.bullIssAfterBreakRunLow is None or low_c < state.bullIssAfterBreakRunLow:
            state.bullIssAfterBreakRunLow = low_c
            state.bullIssAfterBreakRunLowBar = bar_index

        if (state.bullIssAfterBreakRunLow is not None and state.bullIss2Level is not None and
            state.bullIssAfterBreakRunLow < state.bullIss2Level):
            reset_bull_iss(state)

        if (state.bullIssState == 4 and state.bullIssAfterBreakRunHigh is not None and
            state.bullIssAfterBreakRunLowBar is not None and close_c > state.bullIssAfterBreakRunHigh):

            # --- BULLISH ISS CONFIRMED ---
            event_result = "BULL_ISS4_CONFIRMED"
            src_bars = [state.bullIss1Bar, state.bullIss2Bar, state.bullIssAfterBreakRunHighBar, state.bullIssAfterBreakRunLowBar]

            def get_ohlc(b_idx):
                if b_idx in df["bar_index"].values:
                    r = df[df["bar_index"] == b_idx].iloc[0]
                    return r["open"], r["close"], r["high"], r["low"]
                return open_c, close_c, high_c, low_c

            o1, c1, h1, l1 = get_ohlc(state.bullIss1Bar)
            o2, c2, h2, l2 = get_ohlc(state.bullIss2Bar)
            o3, c3, h3, l3 = get_ohlc(state.bullIssAfterBreakRunHighBar)
            o4, c4, h4, l4 = get_ohlc(state.bullIssAfterBreakRunLowBar)

            add_level_from_bar_ready(state.levels, state.bullIss1Bar, o1, c1, h1, l1, True, "yellow", "ISS 1", 29, bar_index, bar_index, bar_index, zone_body_pct)
            add_level_from_bar_ready(state.levels, state.bullIss2Bar, o2, c2, h2, l2, False, "yellow", "ISS 2", 34, bar_index, bar_index, bar_index, zone_body_pct)
            add_level_from_bar_ready(state.levels, state.bullIssAfterBreakRunHighBar, o3, c3, h3, l3, True, "yellow", "ISS 3", 30, bar_index, bar_index, bar_index, zone_body_pct)
            add_level_from_bar_ready(state.levels, state.bullIssAfterBreakRunLowBar, o4, c4, h4, l4, False, "yellow", "ISS 4", 31, bar_index, bar_index, bar_index, zone_body_pct)

            state.trend = 1
            state.phase = 1
            state.lastCH = make_snap_at_bar(state.bullIssAfterBreakRunHighBar, state.bullIssAfterBreakRunHigh, df, bar_index)
            state.lastCL = make_snap_at_bar(state.bullIssAfterBreakRunLowBar, state.bullIssAfterBreakRunLow, df, bar_index)
            state.lastCHSet = True
            state.lastCLSet = True
            state.tjl1 = state.lastCH
            state.tjl2 = state.lastCL
            state.tjl1Set = True
            state.runHigh = make_snap_current(bar_index, open_c, close_c, high_c, low_c, high_c)
            state.runLow = make_snap_current(bar_index, open_c, close_c, high_c, low_c, low_c)
            state.issOrTjlSinceChoch = True

            reset_bull_iss(state)
            reset_bear_iss(state)

    # --- Bearish ISS State Machine ---
    if state.bearIssState == 1:
        if state.bearIssBaseHigh is None or high_c > state.bearIssBaseHigh:
            state.bearIssBaseHigh = high_c
            state.bearIssBaseHighBar = bar_index
            state.bearIssRunLow = low_c
            state.bearIssRunLowBar = bar_index
            state.bearIssBaseConfirmed = False
        if not state.bearIssBaseConfirmed:
            if bearish_shift:
                state.bearIssBaseConfirmed = True
                state.bearIssRunLow = low_c
                state.bearIssRunLowBar = bar_index
        else:
            if state.bearIssRunLow is None or low_c < state.bearIssRunLow:
                state.bearIssRunLow = low_c
                state.bearIssRunLowBar = bar_index
            if bullish_shift and state.bearIssRunLowBar is not None and state.bearIssRunLowBar < bar_index:
                state.bearIss1Level = state.bearIssRunLow
                state.bearIss1Bar = state.bearIssRunLowBar
                state.bearIssState = 2
                state.bearIss2Level = high_c
                state.bearIss2Bar = bar_index

    elif state.bearIssState == 2:
        if state.bearIss2Level is not None and high_c > state.bearIss2Level:
            state.bearIss2Level = high_c
            state.bearIss2Bar = bar_index
        if state.bearIss1Level is not None and close_c < state.bearIss1Level:
            state.bearIssAfterBreakRunLow = low_c
            state.bearIssAfterBreakRunLowBar = bar_index
            state.bearIssAfterBreakRunHigh = high_c
            state.bearIssAfterBreakRunHighBar = bar_index
            state.bearIssState = 3

    elif state.bearIssState == 3:
        if state.bearIss2Level is not None and high_c > state.bearIss2Level:
            state.bearIss2Level = high_c
            state.bearIss2Bar = bar_index
        if state.bearIssAfterBreakRunLow is None or low_c < state.bearIssAfterBreakRunLow:
            state.bearIssAfterBreakRunLow = low_c
            state.bearIssAfterBreakRunLowBar = bar_index
            state.bearIssAfterBreakRunHigh = high_c
            state.bearIssAfterBreakRunHighBar = bar_index
        elif state.bearIssAfterBreakRunHigh is None or high_c > state.bearIssAfterBreakRunHigh:
            state.bearIssAfterBreakRunHigh = high_c
            state.bearIssAfterBreakRunHighBar = bar_index

        if bullish_shift and state.bearIssAfterBreakRunLowBar is not None and state.bearIssAfterBreakRunHighBar is not None:
            state.bearIssState = 4

    elif state.bearIssState == 4:
        if state.bearIssAfterBreakRunHigh is None or high_c > state.bearIssAfterBreakRunHigh:
            state.bearIssAfterBreakRunHigh = high_c
            state.bearIssAfterBreakRunHighBar = bar_index

        if (state.bearIssAfterBreakRunHigh is not None and state.bearIss2Level is not None and
            state.bearIssAfterBreakRunHigh > state.bearIss2Level):
            reset_bear_iss(state)

        if (state.bearIssState == 4 and state.bearIssAfterBreakRunLow is not None and
            state.bearIssAfterBreakRunHighBar is not None and close_c < state.bearIssAfterBreakRunLow):

            # --- BEARISH ISS CONFIRMED ---
            event_result = "BEAR_ISS4_CONFIRMED"

            def get_ohlc_b(b_idx):
                if b_idx in df["bar_index"].values:
                    r = df[df["bar_index"] == b_idx].iloc[0]
                    return r["open"], r["close"], r["high"], r["low"]
                return open_c, close_c, high_c, low_c

            o1, c1, h1, l1 = get_ohlc_b(state.bearIss1Bar)
            o2, c2, h2, l2 = get_ohlc_b(state.bearIss2Bar)
            o3, c3, h3, l3 = get_ohlc_b(state.bearIssAfterBreakRunLowBar)
            o4, c4, h4, l4 = get_ohlc_b(state.bearIssAfterBreakRunHighBar)

            add_level_from_bar_ready(state.levels, state.bearIss1Bar, o1, c1, h1, l1, False, "yellow", "ISS 1", 29, bar_index, bar_index, bar_index, zone_body_pct)
            add_level_from_bar_ready(state.levels, state.bearIss2Bar, o2, c2, h2, l2, True, "yellow", "ISS 2", 35, bar_index, bar_index, bar_index, zone_body_pct)
            add_level_from_bar_ready(state.levels, state.bearIssAfterBreakRunLowBar, o3, c3, h3, l3, False, "yellow", "ISS 3", 32, bar_index, bar_index, bar_index, zone_body_pct)
            add_level_from_bar_ready(state.levels, state.bearIssAfterBreakRunHighBar, o4, c4, h4, l4, True, "yellow", "ISS 4", 33, bar_index, bar_index, bar_index, zone_body_pct)

            state.trend = -1
            state.phase = 1
            state.lastCH = make_snap_at_bar(state.bearIssAfterBreakRunHighBar, state.bearIssAfterBreakRunHigh, df, bar_index)
            state.lastCL = make_snap_at_bar(state.bearIssAfterBreakRunLowBar, state.bearIssAfterBreakRunLow, df, bar_index)
            state.lastCHSet = True
            state.lastCLSet = True
            state.tjl1 = state.lastCL
            state.tjl2 = state.lastCH
            state.tjl1Set = True
            state.runHigh = make_snap_current(bar_index, open_c, close_c, high_c, low_c, high_c)
            state.runLow = make_snap_current(bar_index, open_c, close_c, high_c, low_c, low_c)
            state.issOrTjlSinceChoch = True

            reset_bear_iss(state)
            reset_bull_iss(state)

    return event_result
