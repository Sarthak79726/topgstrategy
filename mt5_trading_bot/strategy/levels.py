from typing import List, Optional, Tuple
import numpy as np
from .state import Level, StrategyState
from .candles import candle_zone, is_tapped

def level_dir(kind: int, is_high: bool) -> int:
    """Return direction integer (+1 for Bullish, -1 for Bearish, 0 neutral)."""
    if kind in (1, 2):
        return 1 if is_high else -1
    elif kind in (4, 6):
        return 1
    elif kind in (3, 5):
        return -1
    elif kind == 7:
        return -1 if is_high else 1
    elif kind in (30, 31, 35):
        return 1
    elif kind in (32, 33, 34):
        return -1
    return 0

def level_display_text(kind: int, direction: int, txt: str) -> str:
    """Format display text for TJL levels."""
    if kind == 1:
        return txt if txt in ("BUY TJL1", "SELL TJL1") else ("BUY TJL1" if direction == 1 else "SELL TJL1")
    elif kind == 2:
        return txt if txt in ("BUY TJL2", "SELL TJL2") else ("BUY TJL2" if direction == 1 else "SELL TJL2")
    return txt

def best_level_text(kind: int, direction: int) -> str:
    """Format promoted D-CHOCH level text."""
    if kind == 3:
        return "D-CHOCH SBR"
    elif kind == 4:
        return "D-CHOCH RBS"
    elif kind == 5:
        return "D-CHOCH DT"
    elif kind == 6:
        return "D-CHOCH DB"
    elif kind == 7 and direction == 1:
        return "D-CHOCH SELL QML"
    elif kind == 7 and direction == -1:
        return "D-CHOCH BUY QML"
    return "D-CHOCH QML"

def add_level(levels: List[Level], left_: int, o: float, c: float, h: float, l: float,
              is_high: bool, col: str, txt: str, kind: int, born_bar: int, right_: int,
              zone_body_pct: float = 1.0):
    """Add a new Level object to the levels list."""
    top_, bot_ = candle_zone(o, c, h, l, is_high, zone_body_pct)
    direction = level_dir(kind, is_high)
    disp_txt = level_display_text(kind, direction, txt)
    lv = Level(
        left=left_, right=right_, top=top_, bot=bot_, col=col, txt=disp_txt,
        kind=kind, dir=direction, active=True, deleted=False, stopReady=False,
        stopReadyBar=0, bornBar=born_bar
    )
    levels.append(lv)

def add_level_from_bar_ready(levels: List[Level], left_bar: int, src_o: float, src_c: float, src_h: float, src_l: float,
                             is_high: bool, col: str, txt: str, kind: int, born_bar: int, right_bar: int, ready_bar: int,
                             zone_body_pct: float = 1.0):
    """Add a Level object with stopReady set to True (used for ISS levels)."""
    top_, bot_ = candle_zone(src_o, src_c, src_h, src_l, is_high, zone_body_pct)
    direction = level_dir(kind, is_high)
    disp_txt = level_display_text(kind, direction, txt)
    lv = Level(
        left=left_bar, right=right_bar, top=top_, bot=bot_, col=col, txt=disp_txt,
        kind=kind, dir=direction, active=True, deleted=False, stopReady=True,
        stopReadyBar=ready_bar, bornBar=born_bar
    )
    levels.append(lv)

def delete_latest_tjl1_by_left(levels: List[Level], src_left_bar: int):
    """Mark the latest TJL1 level matching src_left_bar as deleted."""
    for i in range(len(levels) - 1, -1, -1):
        lv = levels[i]
        if not lv.deleted and lv.active and lv.kind == 1 and lv.left == src_left_bar:
            lv.deleted = True
            lv.active = False
            break

def freeze_previous_choch_levels(levels: List[Level]):
    """Deactivate previous CHOCH levels (kinds 3 to 7)."""
    for lv in levels:
        if not lv.deleted and lv.active and 3 <= lv.kind <= 7:
            lv.active = False

def promote_last_choch_levels_to_best(levels: List[Level], qml_left: Optional[int], bar_index: int):
    """Promote previous CHOCH levels to Best (D-CHOCH) levels upon Dual-CHOCH occurrence."""
    if qml_left is None or len(levels) == 0:
        return

    src_born_bar = None
    for lv in reversed(levels):
        if lv.kind == 7 and not lv.deleted and lv.left == qml_left:
            src_born_bar = lv.bornBar
            break

    if src_born_bar is not None:
        for i in range(len(levels) - 1, -1, -1):
            src_lv = levels[i]
            if 3 <= src_lv.kind <= 7 and not src_lv.deleted and src_lv.bornBar == src_born_bar:
                best_txt = best_level_text(src_lv.kind, src_lv.dir)
                best_col = "gold" if src_lv.kind == 7 else src_lv.col

                src_lv.deleted = True
                src_lv.active = False
                src_lv.txt = ""

                # Check if Best level already exists
                best_found = False
                for j in range(len(levels) - 1, -1, -1):
                    found_best = levels[j]
                    if (found_best.kind == 8 and not found_best.deleted and
                        found_best.left == src_lv.left and found_best.top == src_lv.top and
                        found_best.bot == src_lv.bot and found_best.txt == best_txt):

                        found_best.active = True
                        found_best.right = bar_index
                        found_best.bornBar = bar_index
                        found_best.stopReady = False
                        found_best.stopReadyBar = 0
                        found_best.col = best_col
                        found_best.txt = best_txt
                        found_best.anaStarted = False
                        found_best.anaActive = False
                        best_found = True
                        break

                if not best_found:
                    new_best = Level(
                        left=src_lv.left, right=bar_index, top=src_lv.top, bot=src_lv.bot,
                        col=best_col, txt=best_txt, kind=8, dir=src_lv.dir, active=True,
                        deleted=False, stopReady=False, stopReadyBar=0, bornBar=bar_index
                    )
                    levels.append(new_best)

def update_levels(levels: List[Level], r_open: float, r_close: float, r_high: float, r_low: float,
                  bar_num: int, stop_on_tap: bool = True, tap_source: str = "TapByWick",
                  stop_iss_34_by_wick_tap: bool = True):
    """Update levels active state and tap status per candle."""
    for lv in levels:
        if lv.deleted:
            continue
        if not lv.active:
            continue

        lv.right = bar_num
        iss_wick_level = lv.kind in (30, 31, 32, 33, 34, 35)

        if iss_wick_level:
            if stop_iss_34_by_wick_tap and bar_num > lv.bornBar:
                crossed = (r_close > lv.top) if lv.dir == 1 else (r_close < lv.bot)
                if not lv.stopReady and crossed:
                    lv.stopReady = True
                    lv.stopReadyBar = bar_num
                if lv.stopReady and bar_num > lv.stopReadyBar:
                    iss_tapped = (r_high >= lv.bot and r_low <= lv.top)
                    if iss_tapped:
                        lv.active = False
                        lv.right = bar_num
        else:
            if stop_on_tap and bar_num > lv.bornBar:
                std_tapped = is_tapped(r_close, r_high, r_low, lv.top, lv.bot, tap_source)
                if std_tapped:
                    lv.active = False
                    lv.right = bar_num

def trim_levels(levels: List[Level], max_live_levels: int = 140):
    """Mark older levels as deleted if max live levels limit is exceeded."""
    kept = 0
    for i in range(len(levels) - 1, -1, -1):
        lv = levels[i]
        if lv.deleted:
            continue
        kept += 1
        if kept > max_live_levels:
            lv.deleted = True
            lv.active = False

def compact_deleted_levels(levels: List[Level]):
    """Remove deleted levels from list to keep collection memory compact."""
    i = len(levels) - 1
    while i >= 0:
        if levels[i].deleted:
            levels.pop(i)
        i -= 1
