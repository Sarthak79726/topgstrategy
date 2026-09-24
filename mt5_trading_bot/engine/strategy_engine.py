import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from ..strategy.state import StrategyState, Level, FVGLevel, OBLevel, Snap
from ..strategy.candles import candle_zone, is_tapped
from ..strategy.levels import (
    add_level, add_level_from_bar_ready, delete_latest_tjl1_by_left,
    freeze_previous_choch_levels, promote_last_choch_levels_to_best,
    update_levels, trim_levels, compact_deleted_levels
)
from ..strategy.structure import make_snap_current, make_snap_at_bar, init_snap
from ..strategy.bos_choch import detect_structure_shifts
from ..strategy.iss import update_iss_state
from ..strategy.ema import calculate_ema
from ..strategy.fvg import update_fvg
from ..strategy.order_blocks import update_order_blocks
from ..strategy.analyzer import update_level_analyzer
from ..utils.logger import logger

@dataclass
class TradingSignal:
    timestamp: pd.Timestamp
    bar_index: int
    symbol: str
    timeframe: str
    direction: str  # "BUY" or "SELL"
    entry_price: float
    stop_loss: float
    take_profit: float
    reason: str
    level_kind: int
    level_text: str
    level_top: float
    level_bot: float
    risk_pips: float

class StrategyEngine:
    """
    Main Bar-by-Bar Strategy Engine translating TradingView Pine Script 'RM'S JADU TONA'.
    Executes sequentially over OHLCV data without forward-looking bias.
    """

    def __init__(self, symbol: str = "XAUUSD", timeframe: str = "M5",
                 max_bars: int = 12000, zone_body_pct: float = 1.0,
                 tap_source: str = "TapByWick", stop_on_tap: bool = True,
                 stop_iss_34_by_wick_tap: bool = True, default_rr: float = 2.0,
                 default_sl_pips: float = 50.0):

        self.symbol = symbol
        self.timeframe = timeframe
        self.max_bars = max_bars
        self.zone_body_pct = zone_body_pct
        self.tap_source = tap_source
        self.stop_on_tap = stop_on_tap
        self.stop_iss_34_by_wick_tap = stop_iss_34_by_wick_tap
        self.default_rr = default_rr
        self.default_sl_pips = default_sl_pips

        self.state = StrategyState()
        self.signals: List[TradingSignal] = []

    def reset(self):
        """Reset internal strategy state."""
        self.state = StrategyState()
        self.signals.clear()

    def process_data(self, df: pd.DataFrame) -> List[TradingSignal]:
        """
        Process historical or live DataFrame sequentially bar by bar.
        Expects DataFrame with columns: ['time', 'open', 'high', 'low', 'close']
        """
        if df is None or df.empty or len(df) < 2:
            logger.warning("DataFrame is empty or has insufficient rows for strategy processing.")
            return []

        df = df.copy().reset_index(drop=True)
        df["bar_index"] = np.arange(len(df))

        # Calculate EMAs
        df["ema20"] = calculate_ema(df["close"], 20)
        df["ema50"] = calculate_ema(df["close"], 50)
        df["ema100"] = calculate_ema(df["close"], 100)
        df["ema200"] = calculate_ema(df["close"], 200)

        self.signals.clear()

        # Iterate over bars sequentially starting from bar index 1
        for i in range(1, len(df)):
            self._on_bar(df, i)

        return self.signals

    def _on_bar(self, df: pd.DataFrame, i: int):
        """Execute logic for a single bar index i."""
        row_curr = df.iloc[i]
        row_prev = df.iloc[i - 1]

        o_c, h_c, l_c, c_c = float(row_curr["open"]), float(row_curr["high"]), float(row_curr["low"]), float(row_curr["close"])
        o_p, h_p, l_p, c_p = float(row_prev["open"]), float(row_prev["high"]), float(row_prev["low"]), float(row_prev["close"])
        ts_c = pd.to_datetime(row_curr["time"])

        bar_idx = int(row_curr["bar_index"])

        # 1. Structure Shift Detection
        bullish_shift, bearish_shift = detect_structure_shifts(o_c, c_c, h_c, l_c, o_p, c_p, h_p, l_p)

        red_p = c_p < o_p
        green_p = c_p > o_p
        red_c = c_c < o_c
        green_c = c_c > o_c

        # 2. CHOCH Conditions
        bear_choch = (self.state.trend == 1 and self.state.lastCLSet and red_p and
                      c_p < self.state.lastCL.lvl and c_c < self.state.lastCL.lvl)

        bull_choch = (self.state.trend == -1 and self.state.lastCHSet and green_p and
                      c_p > self.state.lastCH.lvl and c_c > self.state.lastCH.lvl)

        # 3. Main Trend & Structure State Machine
        if bear_choch:
            bear_dual_choch = (self.state.lastChochSide == -1) and (not self.state.issOrTjlSinceChoch)
            if bear_dual_choch:
                promote_last_choch_levels_to_best(self.state.levels, self.state.lastQmlLeft, bar_idx)
            elif self.state.tjl1Set:
                freeze_previous_choch_levels(self.state.levels)
                # Form QML and SBR/RBS levels
                qml_top, qml_bot = candle_zone(self.state.lastCH.o, self.state.lastCH.c, self.state.lastCH.h, self.state.lastCH.l, True, self.zone_body_pct)
                add_level(self.state.levels, self.state.lastCH.bar, self.state.lastCH.o, self.state.lastCH.c, self.state.lastCH.h, self.state.lastCH.l, True, "red", "SELL QML", 7, bar_idx, bar_idx, self.zone_body_pct)
                add_level(self.state.levels, self.state.lastCL.bar, self.state.lastCL.o, self.state.lastCL.c, self.state.lastCL.h, self.state.lastCL.l, False, "maroon", "SBR", 3, bar_idx, bar_idx, self.zone_body_pct)
                self.state.lastQmlLeft = self.state.lastCH.bar
                self.state.lastQmlTop = qml_top
                self.state.lastQmlBot = qml_bot

            self.state.trend = -1
            self.state.phase = 1
            self.state.lastCH = self.state.runHigh
            self.state.lastCHSet = True
            self.state.lastChochSide = 1
            self.state.issOrTjlSinceChoch = False

            self.state.runHigh = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, h_c)
            self.state.runLow = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, l_c)

            self.state.bullIssState = 1
            self.state.bullIssBaseConfirmed = False
            self.state.bullIssBaseLow = l_c
            self.state.bullIssBaseLowBar = bar_idx
            self.state.bearIssState = 0

        elif bull_choch:
            bull_dual_choch = (self.state.lastChochSide == 1) and (not self.state.issOrTjlSinceChoch)
            if bull_dual_choch:
                promote_last_choch_levels_to_best(self.state.levels, self.state.lastQmlLeft, bar_idx)
            elif self.state.tjl1Set:
                freeze_previous_choch_levels(self.state.levels)
                # Form QML and RBS/SBR levels
                qml_top, qml_bot = candle_zone(self.state.lastCL.o, self.state.lastCL.c, self.state.lastCL.h, self.state.lastCL.l, False, self.zone_body_pct)
                add_level(self.state.levels, self.state.lastCL.bar, self.state.lastCL.o, self.state.lastCL.c, self.state.lastCL.h, self.state.lastCL.l, False, "green", "BUY QML", 7, bar_idx, bar_idx, self.zone_body_pct)
                add_level(self.state.levels, self.state.lastCH.bar, self.state.lastCH.o, self.state.lastCH.c, self.state.lastCH.h, self.state.lastCH.l, True, "lime", "RBS", 4, bar_idx, bar_idx, self.zone_body_pct)
                self.state.lastQmlLeft = self.state.lastCL.bar
                self.state.lastQmlTop = qml_top
                self.state.lastQmlBot = qml_bot

            self.state.trend = 1
            self.state.phase = 1
            self.state.lastCL = self.state.runLow
            self.state.lastCLSet = True
            self.state.lastChochSide = -1
            self.state.issOrTjlSinceChoch = False

            self.state.runHigh = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, h_c)
            self.state.runLow = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, l_c)

            self.state.bearIssState = 1
            self.state.bearIssBaseConfirmed = False
            self.state.bearIssBaseHigh = h_c
            self.state.bearIssBaseHighBar = bar_idx
            self.state.bullIssState = 0

        else:
            # Uninitialized trend handling
            if self.state.trend == 0:
                self.state.runHigh = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, h_c)
                self.state.runLow = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, l_c)
                self.state.trend = 1 if c_c > o_c else -1
                self.state.phase = 1

            elif self.state.trend == 1:
                if self.state.phase == 1:
                    if h_c > self.state.runHigh.lvl:
                        self.state.runHigh = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, h_c)
                    if l_c < self.state.runLow.lvl:
                        self.state.runLow = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, l_c)
                    if red_c and bearish_shift:
                        self.state.phase = 2
                        self.state.runLow = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, l_c)

                elif self.state.phase == 2:
                    if l_c < self.state.runLow.lvl:
                        self.state.runLow = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, l_c)
                    if self.state.lastCHSet and c_c > self.state.lastCH.lvl:
                        # Bullish BOS!
                        self.state.lastCL = make_snap_at_bar(self.state.runLow.bar, self.state.runLow.lvl, df, bar_idx)
                        self.state.lastCLSet = True

                        ch_off = bar_idx - self.state.lastCH.bar
                        cl_off = bar_idx - self.state.lastCL.bar

                        self.state.tjl1 = make_snap_at_bar(self.state.lastCH.bar, self.state.lastCH.lvl, df, bar_idx)
                        self.state.tjl2 = make_snap_at_bar(self.state.lastCL.bar, self.state.lastCL.lvl, df, bar_idx)
                        self.state.tjl1Set = True

                        ch_row = df[df["bar_index"] == self.state.lastCH.bar].iloc[0]
                        cl_row = df[df["bar_index"] == self.state.lastCL.bar].iloc[0]

                        add_level(self.state.levels, self.state.tjl1.bar, float(ch_row["open"]), float(ch_row["close"]), float(ch_row["high"]), float(ch_row["low"]), True, "blue", "BUY TJL1", 1, bar_idx, bar_idx, self.zone_body_pct)
                        add_level(self.state.levels, self.state.tjl2.bar, float(cl_row["open"]), float(cl_row["close"]), float(cl_row["high"]), float(cl_row["low"]), False, "blue", "BUY TJL2", 2, bar_idx, bar_idx, self.zone_body_pct)

                        self.state.issOrTjlSinceChoch = True
                        self.state.phase = 1
                        self.state.runHigh = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, h_c)
                        self.state.runLow = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, l_c)

                        self.state.bearIssState = 1
                        self.state.bearIssBaseConfirmed = False
                        self.state.bearIssBaseHigh = h_c
                        self.state.bearIssBaseHighBar = bar_idx

            elif self.state.trend == -1:
                if self.state.phase == 1:
                    if l_c < self.state.runLow.lvl:
                        self.state.runLow = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, l_c)
                    if h_c > self.state.runHigh.lvl:
                        self.state.runHigh = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, h_c)
                    if green_c and bullish_shift:
                        self.state.phase = 2
                        self.state.runHigh = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, h_c)

                elif self.state.phase == 2:
                    if h_c > self.state.runHigh.lvl:
                        self.state.runHigh = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, h_c)
                    if self.state.lastCLSet and c_c < self.state.lastCL.lvl:
                        # Bearish BOS!
                        self.state.lastCH = make_snap_at_bar(self.state.runHigh.bar, self.state.runHigh.lvl, df, bar_idx)
                        self.state.lastCHSet = True

                        ch_row = df[df["bar_index"] == self.state.lastCH.bar].iloc[0]
                        cl_row = df[df["bar_index"] == self.state.lastCL.bar].iloc[0]

                        self.state.tjl1 = make_snap_at_bar(self.state.lastCL.bar, self.state.lastCL.lvl, df, bar_idx)
                        self.state.tjl2 = make_snap_at_bar(self.state.lastCH.bar, self.state.lastCH.lvl, df, bar_idx)
                        self.state.tjl1Set = True

                        add_level(self.state.levels, self.state.tjl1.bar, float(cl_row["open"]), float(cl_row["close"]), float(cl_row["high"]), float(cl_row["low"]), False, "red", "SELL TJL1", 1, bar_idx, bar_idx, self.zone_body_pct)
                        add_level(self.state.levels, self.state.tjl2.bar, float(ch_row["open"]), float(ch_row["close"]), float(ch_row["high"]), float(ch_row["low"]), True, "red", "SELL TJL2", 2, bar_idx, bar_idx, self.zone_body_pct)

                        self.state.issOrTjlSinceChoch = True
                        self.state.phase = 1
                        self.state.runHigh = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, h_c)
                        self.state.runLow = make_snap_current(bar_idx, o_c, c_c, h_c, l_c, l_c)

                        self.state.bullIssState = 1
                        self.state.bullIssBaseConfirmed = False
                        self.state.bullIssBaseLow = l_c
                        self.state.bullIssBaseLowBar = bar_idx

        # 4. Update ISS State Machines
        update_iss_state(self.state, bar_idx, o_c, c_c, h_c, l_c, bullish_shift, bearish_shift, df, True, self.zone_body_pct)

        # 5. Update FVG & Order Blocks
        update_fvg(self.state, df, bar_idx)
        update_order_blocks(self.state, df, bar_idx)

        # 6. Check Taps & Level Updates
        update_levels(self.state.levels, o_c, c_c, h_c, l_c, bar_idx, self.stop_on_tap, self.tap_source, self.stop_iss_34_by_wick_tap)
        trim_levels(self.state.levels, max_live_levels=140)
        compact_deleted_levels(self.state.levels)

        # 7. Check Level Touch Signal Generation
        self._check_signals(ts_c, bar_idx, o_c, c_c, h_c, l_c)

    def _check_signals(self, timestamp: pd.Timestamp, bar_idx: int, o: float, c: float, h: float, l: float):
        """Evaluate signal conditions on the current bar."""
        for lv in self.state.levels:
            if lv.deleted or not lv.active or bar_idx <= lv.bornBar:
                continue

            tapped = is_tapped(c, h, l, lv.top, lv.bot, self.tap_source)
            if tapped:
                direction = "BUY" if lv.dir == 1 else ("SELL" if lv.dir == -1 else None)
                if direction is None:
                    continue

                entry_price = lv.top if direction == "BUY" else lv.bot
                sl_dist = (lv.top - lv.bot) if (lv.top - lv.bot) > 0 else (entry_price * 0.002)
                stop_loss = entry_price - sl_dist if direction == "BUY" else entry_price + sl_dist
                take_profit = entry_price + (sl_dist * self.default_rr) if direction == "BUY" else entry_price - (sl_dist * self.default_rr)
                risk_pips = abs(entry_price - stop_loss)

                sig = TradingSignal(
                    timestamp=timestamp,
                    bar_index=bar_idx,
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    direction=direction,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    reason=f"Tap on active level {lv.txt} (Kind {lv.kind})",
                    level_kind=lv.kind,
                    level_text=lv.txt,
                    level_top=lv.top,
                    level_bot=lv.bot,
                    risk_pips=risk_pips
                )
                self.signals.append(sig)
