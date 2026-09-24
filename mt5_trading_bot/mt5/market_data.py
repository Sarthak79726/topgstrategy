from datetime import datetime, timezone
import pandas as pd
import numpy as np
from typing import Optional
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

from ..utils.logger import logger
from ..utils.time_utils import parse_timeframe

MT5_TIMEFRAME_MAP = {}
if MT5_AVAILABLE:
    MT5_TIMEFRAME_MAP = {
        "1": getattr(mt5, "TIMEFRAME_M1", 1),
        "3": getattr(mt5, "TIMEFRAME_M3", 3),
        "5": getattr(mt5, "TIMEFRAME_M5", 5),
        "15": getattr(mt5, "TIMEFRAME_M15", 15),
        "30": getattr(mt5, "TIMEFRAME_M30", 30),
        "45": getattr(mt5, "TIMEFRAME_M30", 30),
        "60": getattr(mt5, "TIMEFRAME_H1", 16385),
        "120": getattr(mt5, "TIMEFRAME_H2", 16386),
        "180": getattr(mt5, "TIMEFRAME_H3", 16387),
        "240": getattr(mt5, "TIMEFRAME_H4", 16388),
        "D": getattr(mt5, "TIMEFRAME_D1", 16408),
        "W": getattr(mt5, "TIMEFRAME_W1", 32769),
        "M": getattr(mt5, "TIMEFRAME_MN1", 49153),
    }

class MarketDataManager:
    """Handles fetching historical OHLCV data and real-time tick data from MT5."""

    def __init__(self, connection=None, symbol: str = "XAUUSD"):
        self.connection = connection
        self.symbol = symbol

    def get_rates_dataframe(self, symbol: Optional[str] = None, timeframe: str = "M5", count: int = 1000) -> Optional[pd.DataFrame]:
        return self.fetch_ohlcv(symbol=symbol, timeframe=timeframe, num_bars=count)

    @staticmethod
    def get_mt5_timeframe(tf_str: str):
        """Map standard timeframe string to MT5 timeframe constant."""
        normalized = parse_timeframe(tf_str)
        if MT5_AVAILABLE:
            return MT5_TIMEFRAME_MAP.get(normalized, mt5.TIMEFRAME_M5)
        return normalized

    def fetch_ohlcv(self, symbol: Optional[str] = None, timeframe: str = "M5", num_bars: int = 1000) -> Optional[pd.DataFrame]:
        """Fetch latest OHLCV bars as pandas DataFrame from MT5."""
        target_sym = symbol or self.symbol
        if not MT5_AVAILABLE:
            logger.warning("MT5 package unavailable. Cannot fetch live OHLCV data.")
            return None

        mt5_tf = self.get_mt5_timeframe(timeframe)
        sym_info = mt5.symbol_info(target_sym)
        if sym_info is None:
            logger.error(f"Symbol '{target_sym}' is not available in MetaTrader 5.")
            return None

        mt5.symbol_select(target_sym, True)
        rates = mt5.copy_rates_from_pos(target_sym, mt5_tf, 0, num_bars)

        if rates is None or len(rates) == 0:
            err_code, err_msg = mt5.last_error()
            logger.error(f"Failed to fetch rates for {target_sym} ({timeframe}): ({err_code}, '{err_msg}')")
            if err_code == -10004 or "ipc" in str(err_msg).lower():
                if self.connection and hasattr(self.connection, "handle_ipc_error"):
                    self.connection.handle_ipc_error(err_code, err_msg)
            return None

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df.rename(columns={"tick_volume": "volume"}, inplace=True)
        df["bar_index"] = np.arange(len(df))

        required_cols = ["time", "open", "high", "low", "close", "volume", "bar_index"]
        return df[required_cols]

    def get_latest_tick(self, symbol: Optional[str] = None) -> Optional[dict]:
        """Fetch current bid, ask, last tick for symbol."""
        target_sym = symbol or self.symbol
        if not MT5_AVAILABLE:
            return None

        tick = mt5.symbol_info_tick(target_sym)
        if tick is None:
            return None

        return {
            "time": tick.time,
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last,
            "volume": tick.volume,
            "spread_pips": tick.ask - tick.bid
        }

MT5MarketData = MarketDataManager
