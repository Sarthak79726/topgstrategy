import pandas as pd
import numpy as np
from typing import Tuple, Optional

def calculate_ema(series: pd.Series, length: int = 132) -> pd.Series:
    """Calculate exponential moving average (ta.ema)."""
    return series.ewm(span=length, adjust=False).mean()

def calculate_sma(series: pd.Series, length: int) -> pd.Series:
    """Calculate simple moving average (ta.sma)."""
    return series.rolling(window=length).mean()

def calculate_rma(series: pd.Series, length: int) -> pd.Series:
    """Calculate Wilder's smoothed moving average / SMMA (ta.rma)."""
    return series.ewm(alpha=1.0 / length, adjust=False).mean()

def calculate_wma(series: pd.Series, length: int) -> pd.Series:
    """Calculate weighted moving average (ta.wma)."""
    weights = np.arange(1, length + 1)
    return series.rolling(window=length).apply(lambda s: np.dot(s, weights) / weights.sum(), raw=True)

def calculate_vwma(price: pd.Series, volume: pd.Series, length: int) -> pd.Series:
    """Calculate volume-weighted moving average (ta.vwma)."""
    pv = price * volume
    return pv.rolling(window=length).sum() / volume.rolling(window=length).sum()

def calculate_ema_system(df: pd.DataFrame, ema_length: int = 132, src_col: str = "close",
                         ma_type: str = "None", ma_length: int = 14, bb_mult: float = 2.0) -> pd.DataFrame:
    """
    Calculate main EMA and optional smoothing MA / Bollinger Bands.
    Direct reproduction of Pine Script EMA section.
    """
    res = df.copy()
    src = res[src_col]
    res["ema"] = calculate_ema(src, ema_length)

    if ma_type == "SMA" or ma_type == "SMA + Bollinger Bands":
        res["ema_ma"] = calculate_sma(res["ema"], ma_length)
    elif ma_type == "EMA":
        res["ema_ma"] = calculate_ema(res["ema"], ma_length)
    elif ma_type == "SMMA (RMA)":
        res["ema_ma"] = calculate_rma(res["ema"], ma_length)
    elif ma_type == "WMA":
        res["ema_ma"] = calculate_wma(res["ema"], ma_length)
    elif ma_type == "VWMA" and "volume" in res.columns:
        res["ema_ma"] = calculate_vwma(res["ema"], res["volume"], ma_length)
    else:
        res["ema_ma"] = np.nan

    if ma_type == "SMA + Bollinger Bands":
        stdev = res["ema"].rolling(window=ma_length).std() * bb_mult
        res["ema_bb_upper"] = res["ema_ma"] + stdev
        res["ema_bb_lower"] = res["ema_ma"] - stdev
    else:
        res["ema_bb_upper"] = np.nan
        res["ema_bb_lower"] = np.nan

    return res
