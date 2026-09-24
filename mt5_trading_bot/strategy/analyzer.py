from typing import List, Optional
from .state import Level, StrategyState
from .candles import is_tapped

SLOTS = [
    "BUY TJL1", "BUY TJL2", "SELL TJL1", "SELL TJL2",
    "SBR", "RBS", "DT", "DB",
    "BUY QML", "SELL QML", "ISS 4",
    "D-CHOCH SBR", "D-CHOCH RBS", "D-CHOCH DT", "D-CHOCH DB",
    "D-CHOCH SELL QML", "D-CHOCH BUY QML"
]

def analyzer_slot(txt: str) -> int:
    """Get slot index (0 to 16) for level label string."""
    try:
        return SLOTS.index(txt)
    except ValueError:
        return -1

def update_level_analyzer(lv: Level, r_open: float, r_close: float, r_high: float, r_low: float,
                          bar_num: int, state: StrategyState, target_pips: float = 150.0,
                          loss_pips: float = 50.0, pip_size: float = 0.1,
                          show_analyzer: bool = False, tap_source: str = "TapByWick"):
    """
    Evaluate win/loss targets for levels once tapped.
    Direct reproduction of Pine Script f_updateLevelAnalyzer().
    """
    if not show_analyzer:
        return

    slot = analyzer_slot(lv.txt)
    if slot < 0 or lv.dir == 0:
        return

    target_move = target_pips * pip_size
    loss_move = loss_pips * pip_size
    tapped = is_tapped(r_close, r_high, r_low, lv.top, lv.bot, tap_source)

    if not lv.anaStarted and bar_num > lv.bornBar and tapped:
        lv.anaStarted = True
        lv.anaWaitingConfirm = False
        lv.anaActive = True
        lv.anaStartBar = bar_num
        lv.anaTargetPrice = (r_close + target_move) if lv.dir == 1 else (r_close - target_move)
        lv.anaLossPrice = (r_low - loss_move) if lv.dir == 1 else (r_high + loss_move)
        state.levelAnalyzerTests[slot] += 1

    if lv.anaActive and lv.anaTargetPrice is not None and lv.anaLossPrice is not None:
        win = (r_high >= lv.anaTargetPrice) if lv.dir == 1 else (r_low <= lv.anaTargetPrice)
        loss = (r_low <= lv.anaLossPrice) if lv.dir == 1 else (r_high >= lv.anaLossPrice)

        result = 0
        if win and not loss:
            result = 1
        elif loss and not win:
            result = -1
        elif win and loss:
            high_first = abs(r_open - r_high) < abs(r_open - r_low)
            if lv.dir == 1:
                result = 1 if high_first else -1
            else:
                result = -1 if high_first else 1

        if result == -1:
            state.levelAnalyzerLosses[slot] += 1
            lv.anaActive = False
        elif result == 1:
            state.levelAnalyzerWins[slot] += 1
            lv.anaActive = False
