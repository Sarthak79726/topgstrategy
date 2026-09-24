from typing import Optional, List, Set, Dict, Any
import pandas as pd
from .signal import Signal
from ..strategy.state import StrategyState, Level
from ..strategy.bos_choch import StructureEvent
from ..strategy.candles import is_tapped
from ..utils.logger import logger, log_signal_to_csv

class SignalGenerator:
    """Evaluates strategy state and structure events to produce validated trading Signals."""

    def __init__(self, symbol: str = "XAUUSD", timeframe: str = "M5",
                 default_sl_pips: float = 50.0, default_tp_pips: float = 150.0,
                 pip_size: float = 0.1):
        self.symbol = symbol
        self.timeframe = timeframe
        self.default_sl_pips = default_sl_pips
        self.default_tp_pips = default_tp_pips
        self.pip_size = pip_size
        self.processed_signal_ids: Set[str] = set()

    def generate_signal(self, state: StrategyState, events: List[StructureEvent],
                        df: pd.DataFrame, bar_index: int,
                        tap_source: str = "TapByWick") -> Optional[Signal]:
        """Generate actionable Signal for current closed bar if setup conditions align."""
        if len(df) == 0:
            return None

        curr = df.iloc[-1]
        r_close = float(curr["close"])
        r_high = float(curr["high"])
        r_low = float(curr["low"])

        direction = "NO_TRADE"
        reason = ""
        component = ""
        sl_price = 0.0
        tp_price = 0.0

        # Check Structure Events (ISS4 Confirmed)
        for ev in events:
            if ev.type == "BULL_ISS4_CONFIRMED":
                direction = "BUY"
                component = "BULL_ISS4_CONFIRMED"
                reason = "Bullish ISS 4 state pattern confirmed"
                sl_price = r_low - (self.default_sl_pips * self.pip_size)
                tp_price = r_close + (self.default_tp_pips * self.pip_size)
                break
            elif ev.type == "BEAR_ISS4_CONFIRMED":
                direction = "SELL"
                component = "BEAR_ISS4_CONFIRMED"
                reason = "Bearish ISS 4 state pattern confirmed"
                sl_price = r_high + (self.default_sl_pips * self.pip_size)
                tp_price = r_close - (self.default_tp_pips * self.pip_size)
                break

        # Check Active Level Taps if no event signal
        if direction == "NO_TRADE":
            for lv in state.levels:
                if not lv.active or lv.deleted or bar_index <= lv.bornBar:
                    continue

                tapped = is_tapped(r_close, r_high, r_low, lv.top, lv.bot, tap_source)
                if tapped:
                    # Alignment check
                    if lv.dir == 1 and state.trend >= 0:
                        direction = "BUY"
                        component = f"{lv.txt}_TAP"
                        reason = f"Price tapped bullish level '{lv.txt}' aligned with trend"
                        sl_price = min(lv.bot, r_low) - (10.0 * self.pip_size)
                        tp_price = r_close + (self.default_tp_pips * self.pip_size)
                        break
                    elif lv.dir == -1 and state.trend <= 0:
                        direction = "SELL"
                        component = f"{lv.txt}_TAP"
                        reason = f"Price tapped bearish level '{lv.txt}' aligned with trend"
                        sl_price = max(lv.top, r_high) + (10.0 * self.pip_size)
                        tp_price = r_close - (self.default_tp_pips * self.pip_size)
                        break

        if direction == "NO_TRADE":
            return None

        sig = Signal(
            symbol=self.symbol,
            timeframe=self.timeframe,
            bar_index=bar_index,
            direction=direction,
            entry_price=r_close,
            stop_loss=sl_price,
            take_profit=tp_price,
            strategy_component=component,
            reason=reason,
            confidence_metadata={"trend": state.trend, "phase": state.phase}
        )

        # Duplicate signal prevention
        if sig.signal_id in self.processed_signal_ids:
            return None

        self.processed_signal_ids.add(sig.signal_id)
        logger.info(f"Signal Generated: {sig.direction} on {sig.symbol} ({sig.timeframe}) via {sig.strategy_component} @ {sig.entry_price}")
        log_signal_to_csv({
            "timestamp": sig.timestamp,
            "symbol": sig.symbol,
            "timeframe": sig.timeframe,
            "signal_id": sig.signal_id,
            "direction": sig.direction,
            "entry": sig.entry_price,
            "stop_loss": sig.stop_loss,
            "take_profit": sig.take_profit,
            "strategy_component": sig.strategy_component,
            "reason": sig.reason
        })

        return sig
