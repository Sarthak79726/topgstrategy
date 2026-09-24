import pandas as pd
import numpy as np
from typing import Dict, Any, List
from .ema import calculate_ema

def calculate_mtf_ema_trend(df_htf: pd.DataFrame, ema_len: int = 132) -> int:
    """
    Calculate EMA trend for higher timeframe (1 if close > ema, -1 if close < ema, 0 neutral).
    Direct reproduction of Pine Script f_dashEmaTrendCalc().
    """
    if df_htf is None or len(df_htf) < ema_len:
        return 0

    ema_series = calculate_ema(df_htf["close"], ema_len)
    last_close = float(df_htf["close"].iloc[-1])
    last_ema = float(ema_series.iloc[-1])

    if last_close > last_ema:
        return 1
    elif last_close < last_ema:
        return -1
    return 0
