import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
from .state import StrategyState, Level, FVGLevel, OBLevel
from .structure import make_snap_current, make_snap_at_bar
from .candles import candle_zone
from .levels import (
    add_level, update_levels, trim_levels, compact_deleted_levels,
    delete_latest_tjl1_by_left, freeze_previous_choch_levels, promote_last_choch_levels_to_best
)
from .fvg import update_fvg
from .order_blocks import create_order_block, update_order_blocks
from .iss import update_iss_state, reset_bull_iss, reset_bear_iss
from .analyzer import update_level_analyzer
from .bos_choch import detect_structure_shifts, StructureEvent
from ..utils.logger import logger

class StrategyEngine:
    """
    Stateful execution engine reproducing TradingView Pine Script v6 strategy "RM'S JADU TONA".
    Processes candles sequentially bar-by-bar without look-ahead bias.
    """

    def __init__(self, config_obj: Any = None):
        self.config = config_obj
        self.state = StrategyState()

        # Strategy options
        self.zone_body_pct = getattr(config_obj, "ZONE_BODY_PCT", 1.0)
        self.stop_on_tap = getattr(config_obj, "STOP_ON_TAP", True)
        self.tap_source = getattr(config_obj, "TAP_SOURCE", "TapByWick")
        self.enable_iss = getattr(config_obj, "ENABLE_ISS", True)
        self.stop_iss_34_by_wick_tap = getattr(config_obj, "STOP_ISS_34_BY_WICK_TAP", True)
        self.show_fvg = getattr(config_obj, "SHOW_FVG", False)
        self.fvg_delete_on_tap = getattr(config_obj, "FVG_DELETE_ON_TAP", True)
        self.max_fvg = getattr(config_obj, "MAX_FVG", 30)
        self.show_ob = getattr(config_obj, "SHOW_OB", False)
        self.ob_delete_on_tap = getattr(config_obj, "OB_DELETE_ON_TAP", True)
        self.max_ob = getattr(config_obj, "MAX_OB", 20)
        self.max_live_levels = getattr(config_obj, "MAX_LIVE_LEVELS", 140)
        self.show_analyzer = getattr(config_obj, "SHOW_LEVEL_ANALYZER", False)
        self.analyzer_target_pips = getattr(config_obj, "ANALYZER_TARGET_PIPS", 150.0)
        self.analyzer_loss_pips = getattr(config_obj, "ANALYZER_LOSS_PIPS", 50.0)

    def process_bar(self, df: pd.DataFrame, bar_index: int) -> List[StructureEvent]:
        """
        Process single closed candle sequentially.
        Main entry point for strategy state updates.
        """
        events: List[StructureEvent] = []

        if len(df) < 2:
            return events

        # Set start bar index if not set
        if self.state.startBarIndex is None:
            self.state.startBarIndex = bar_index

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        open_c, high_c, low_c, close_c = float(curr["open"]), float(curr["high"]), float(curr["low"]), float(curr["close"])
        open_p, high_p, low_p, close_p = float(prev["open"]), float(prev["high"]), float(prev["low"]), float(prev["close"])

        # 1. Update Levels active state & taps
        update_levels(self.state.levels, open_c, close_c, high_c, low_c, bar_index,
                      self.stop_on_tap, self.tap_source, self.stop_iss_34_by_wick_tap)

        # 2. Update SMC FVGs and OBs
        if self.show_fvg:
            update_fvg(self.state, df, bar_index, self.show_fvg, self.fvg_delete_on_tap, self.max_fvg, self.tap_source)
        if self.show_ob:
            update_order_blocks(self.state, df, bar_index, self.show_ob, self.ob_delete_on_tap, self.max_ob, self.tap_source)

        # 3. Update Run High / Low
        if not self.state.runHighSet or high_c > self.state.runHigh.lvl:
            self.state.runHigh = make_snap_current(bar_index, open_c, close_c, high_c, low_c, high_c)
            self.state.runHighSet = True

        if not self.state.runLowSet or low_c < self.state.runLow.lvl:
            self.state.runLow = make_snap_current(bar_index, open_c, close_c, high_c, low_c, low_c)
            self.state.runLowSet = True

        # 4. Shifts and Retracements
        bullish_shift, bearish_shift = detect_structure_shifts(open_c, close_c, high_c, low_c, open_p, close_p, high_p, low_p)
        bull_retracement = bearish_shift
        bear_retracement = bullish_shift

        # 5. CHOCH Conditions
        red_p = close_p < open_p
        green_p = close_p > open_p

        bear_choch = (self.state.trend == 1 and self.state.lastCLSet and red_p and
                      close_p < self.state.lastCL.lvl and close_c < self.state.lastCL.lvl)

        bull_choch = (self.state.trend == -1 and self.state.lastCHSet and green_p and
                      close_p > self.state.lastCH.lvl and close_c > self.state.lastCH.lvl)

        if bear_choch:
            dual_choch_hit = (self.state.lastChochSide == -1 and not self.state.issOrTjlSinceChoch)
            events.append(StructureEvent(type="BEARISH_CHOCH", bar_index=bar_index, price=close_c, dual_choch=dual_choch_hit))

            if self.state.tjl1Set:
                delete_latest_tjl1_by_left(self.state.levels, self.state.tjl1.bar)

            if dual_choch_hit:
                promote_last_choch_levels_to_best(self.state.levels, self.state.lastQmlLeft, bar_index)
                rh_off = bar_index - self.state.runHigh.bar
                if rh_off >= 0 and self.state.runHigh.bar in df["bar_index"].values:
                    r_rh = df[df["bar_index"] == self.state.runHigh.bar].iloc[0]
                    add_level(self.state.levels, self.state.runHigh.bar, float(r_rh["open"]), float(r_rh["close"]),
                              float(r_rh["high"]), float(r_rh["low"]), True, "blue", "D-CHOCH DT", 5, bar_index, bar_index, self.zone_body_pct)
            else:
                freeze_previous_choch_levels(self.state.levels)
                # Add SBR
                if self.state.lastCL.bar in df["bar_index"].values:
                    r_cl = df[df["bar_index"] == self.state.lastCL.bar].iloc[0]
                    add_level(self.state.levels, self.state.lastCL.bar, float(r_cl["open"]), float(r_cl["close"]),
                              float(r_cl["high"]), float(r_cl["low"]), False, "red", "SBR", 3, bar_index, bar_index, self.zone_body_pct)
                # Add DT
                if self.state.runHigh.bar != self.state.tjl1.bar and self.state.runHigh.bar in df["bar_index"].values:
                    r_rh = df[df["bar_index"] == self.state.runHigh.bar].iloc[0]
                    add_level(self.state.levels, self.state.runHigh.bar, float(r_rh["open"]), float(r_rh["close"]),
                              float(r_rh["high"]), float(r_rh["low"]), True, "blue", "DT", 5, bar_index, bar_index, self.zone_body_pct)
                # Add SELL QML
                if self.state.tjl1Set and self.state.tjl1.bar in df["bar_index"].values:
                    r_tj = df[df["bar_index"] == self.state.tjl1.bar].iloc[0]
                    add_level(self.state.levels, self.state.tjl1.bar, float(r_tj["open"]), float(r_tj["close"]),
                              float(r_tj["high"]), float(r_tj["low"]), True, "purple", "SELL QML", 7, bar_index, bar_index, self.zone_body_pct)
                    self.state.lastQmlLeft = self.state.tjl1.bar
                    self.state.lastQmlTop = float(r_tj["high"])
                    self.state.lastQmlBot = float(r_tj["low"])

            if self.show_ob:
                create_order_block(self.state, df, bar_index, is_bullish=False)

            self.state.trend = -1
            self.state.phase = 1
            self.state.lastCH = make_snap_at_bar(self.state.runHigh.bar, self.state.runHigh.lvl, df, bar_index)
            self.state.lastCHSet = True
            self.state.runHigh = make_snap_current(bar_index, open_c, close_c, high_c, low_c, high_c)
            self.state.runLow = make_snap_current(bar_index, open_c, close_c, high_c, low_c, low_c)
            self.state.lastChochSide = 1
            self.state.issOrTjlSinceChoch = False

            reset_bull_iss(self.state)
            reset_bear_iss(self.state)

        elif bull_choch:
            dual_choch_hit = (self.state.lastChochSide == 1 and not self.state.issOrTjlSinceChoch)
            events.append(StructureEvent(type="BULLISH_CHOCH", bar_index=bar_index, price=close_c, dual_choch=dual_choch_hit))

            if self.state.tjl1Set:
                delete_latest_tjl1_by_left(self.state.levels, self.state.tjl1.bar)

            if dual_choch_hit:
                promote_last_choch_levels_to_best(self.state.levels, self.state.lastQmlLeft, bar_index)
                if self.state.runLow.bar in df["bar_index"].values:
                    r_rl = df[df["bar_index"] == self.state.runLow.bar].iloc[0]
                    add_level(self.state.levels, self.state.runLow.bar, float(r_rl["open"]), float(r_rl["close"]),
                              float(r_rl["high"]), float(r_rl["low"]), False, "blue", "D-CHOCH DB", 6, bar_index, bar_index, self.zone_body_pct)
            else:
                freeze_previous_choch_levels(self.state.levels)
                # Add RBS
                if self.state.lastCH.bar in df["bar_index"].values:
                    r_ch = df[df["bar_index"] == self.state.lastCH.bar].iloc[0]
                    add_level(self.state.levels, self.state.lastCH.bar, float(r_ch["open"]), float(r_ch["close"]),
                              float(r_ch["high"]), float(r_ch["low"]), True, "green", "RBS", 4, bar_index, bar_index, self.zone_body_pct)
                # Add DB
                if self.state.runLow.bar != self.state.tjl1.bar and self.state.runLow.bar in df["bar_index"].values:
                    r_rl = df[df["bar_index"] == self.state.runLow.bar].iloc[0]
                    add_level(self.state.levels, self.state.runLow.bar, float(r_rl["open"]), float(r_rl["close"]),
                              float(r_rl["high"]), float(r_rl["low"]), False, "blue", "DB", 6, bar_index, bar_index, self.zone_body_pct)
                # Add BUY QML
                if self.state.tjl1Set and self.state.tjl1.bar in df["bar_index"].values:
                    r_tj = df[df["bar_index"] == self.state.tjl1.bar].iloc[0]
                    add_level(self.state.levels, self.state.tjl1.bar, float(r_tj["open"]), float(r_tj["close"]),
                              float(r_tj["high"]), float(r_tj["low"]), False, "purple", "BUY QML", 7, bar_index, bar_index, self.zone_body_pct)
                    self.state.lastQmlLeft = self.state.tjl1.bar
                    self.state.lastQmlTop = float(r_tj["high"])
                    self.state.lastQmlBot = float(r_tj["low"])

            if self.show_ob:
                create_order_block(self.state, df, bar_index, is_bullish=True)

            self.state.trend = 1
            self.state.phase = 1
            self.state.lastCL = make_snap_at_bar(self.state.runLow.bar, self.state.runLow.lvl, df, bar_index)
            self.state.lastCLSet = True
            self.state.runHigh = make_snap_current(bar_index, open_c, close_c, high_c, low_c, high_c)
            self.state.runLow = make_snap_current(bar_index, open_c, close_c, high_c, low_c, low_c)
            self.state.lastChochSide = -1
            self.state.issOrTjlSinceChoch = False

            reset_bull_iss(self.state)
            reset_bear_iss(self.state)

        else:
            # 6. BOS Conditions
            if self.state.trend == 1 and self.state.phase == 2 and self.state.lastCHSet and close_c > self.state.lastCH.lvl:
                events.append(StructureEvent(type="BULLISH_BOS", bar_index=bar_index, price=close_c))
                self.state.lastCL = make_snap_at_bar(self.state.runLow.bar, self.state.runLow.lvl, df, bar_index)
                self.state.lastCLSet = True
                self.state.tjl1 = make_snap_at_bar(self.state.lastCH.bar, self.state.lastCH.lvl, df, bar_index)
                self.state.tjl2 = make_snap_at_bar(self.state.lastCL.bar, self.state.lastCL.lvl, df, bar_index)
                self.state.tjl1Set = True

                if self.state.lastCH.bar in df["bar_index"].values:
                    r_ch2 = df[df["bar_index"] == self.state.lastCH.bar].iloc[0]
                    add_level(self.state.levels, self.state.tjl1.bar, float(r_ch2["open"]), float(r_ch2["close"]),
                              float(r_ch2["high"]), float(r_ch2["low"]), True, "green", "BUY TJL1", 1, bar_index, bar_index, self.zone_body_pct)
                if self.state.lastCL.bar in df["bar_index"].values:
                    r_cl2 = df[df["bar_index"] == self.state.lastCL.bar].iloc[0]
                    add_level(self.state.levels, self.state.tjl2.bar, float(r_cl2["open"]), float(r_cl2["close"]),
                              float(r_cl2["high"]), float(r_cl2["low"]), False, "green", "BUY TJL2", 2, bar_index, bar_index, self.zone_body_pct)

                self.state.issOrTjlSinceChoch = True
                if self.show_ob:
                    create_order_block(self.state, df, bar_index, is_bullish=True)

                self.state.phase = 1
                self.state.runHigh = make_snap_current(bar_index, open_c, close_c, high_c, low_c, high_c)
                self.state.runLow = make_snap_current(bar_index, open_c, close_c, high_c, low_c, low_c)
                reset_bear_iss(self.state)
                reset_bull_iss(self.state)

            elif self.state.trend == -1 and self.state.phase == 2 and self.state.lastCLSet and close_c < self.state.lastCL.lvl:
                events.append(StructureEvent(type="BEARISH_BOS", bar_index=bar_index, price=close_c))
                self.state.lastCH = make_snap_at_bar(self.state.runHigh.bar, self.state.runHigh.lvl, df, bar_index)
                self.state.lastCHSet = True
                self.state.tjl1 = make_snap_at_bar(self.state.lastCL.bar, self.state.lastCL.lvl, df, bar_index)
                self.state.tjl2 = make_snap_at_bar(self.state.lastCH.bar, self.state.lastCH.lvl, df, bar_index)
                self.state.tjl1Set = True

                if self.state.lastCL.bar in df["bar_index"].values:
                    r_cl2 = df[df["bar_index"] == self.state.lastCL.bar].iloc[0]
                    add_level(self.state.levels, self.state.tjl1.bar, float(r_cl2["open"]), float(r_cl2["close"]),
                              float(r_cl2["high"]), float(r_cl2["low"]), False, "orange", "SELL TJL1", 1, bar_index, bar_index, self.zone_body_pct)
                if self.state.lastCH.bar in df["bar_index"].values:
                    r_ch2 = df[df["bar_index"] == self.state.lastCH.bar].iloc[0]
                    add_level(self.state.levels, self.state.tjl2.bar, float(r_ch2["open"]), float(r_ch2["close"]),
                              float(r_ch2["high"]), float(r_ch2["low"]), True, "orange", "SELL TJL2", 2, bar_index, bar_index, self.zone_body_pct)

                self.state.issOrTjlSinceChoch = True
                if self.show_ob:
                    create_order_block(self.state, df, bar_index, is_bullish=False)

                self.state.phase = 1
                self.state.runHigh = make_snap_current(bar_index, open_c, close_c, high_c, low_c, high_c)
                self.state.runLow = make_snap_current(bar_index, open_c, close_c, high_c, low_c, low_c)
                reset_bull_iss(self.state)
                reset_bear_iss(self.state)

            elif self.state.phase == 1:
                # 7. Retracement Phase 1 -> Phase 2
                if self.state.trend != -1 and bull_retracement:
                    self.state.lastCH = make_snap_at_bar(self.state.runHigh.bar, self.state.runHigh.lvl, df, bar_index)
                    self.state.lastCHSet = True
                    self.state.trend = 1
                    self.state.phase = 2
                    if low_c < low_p:
                        self.state.runLow = make_snap_current(bar_index, open_c, close_c, high_c, low_c, low_c)
                    else:
                        self.state.runLow = make_snap_at_bar(bar_index - 1, low_p, df, bar_index)
                elif self.state.trend != 1 and bear_retracement:
                    self.state.lastCL = make_snap_at_bar(self.state.runLow.bar, self.state.runLow.lvl, df, bar_index)
                    self.state.lastCLSet = True
                    self.state.trend = -1
                    self.state.phase = 2
                    if high_c > high_p:
                        self.state.runHigh = make_snap_current(bar_index, open_c, close_c, high_c, low_c, high_c)
                    else:
                        self.state.runHigh = make_snap_at_bar(bar_index - 1, high_p, df, bar_index)

        # 8. ISS State Machine Execution
        iss_event = update_iss_state(self.state, bar_index, open_c, close_c, high_c, low_c,
                                     bullish_shift, bearish_shift, df, self.enable_iss, self.zone_body_pct)
        if iss_event:
            events.append(StructureEvent(type=iss_event, bar_index=bar_index, price=close_c))

        # 9. Analyzer update per level
        if self.show_analyzer:
            for lv in self.state.levels:
                if not lv.deleted and lv.active:
                    update_level_analyzer(lv, open_c, close_c, high_c, low_c, bar_index, self.state,
                                          self.analyzer_target_pips, self.analyzer_loss_pips,
                                          0.1, self.show_analyzer, self.tap_source)

        # 10. Trim and compact collections
        trim_levels(self.state.levels, self.max_live_levels)
        compact_deleted_levels(self.state.levels)

        return events
