import pytest
import pandas as pd
import numpy as np
from mt5_trading_bot.strategy.ema import calculate_ema, calculate_sma, calculate_wma, calculate_ema_system

def test_calculate_ema():
    prices = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0])
    ema = calculate_ema(prices, length=3)
    assert len(ema) == len(prices)
    assert not pd.isna(ema.iloc[-1])
    assert ema.iloc[-1] > ema.iloc[0]

def test_calculate_sma():
    prices = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    sma = calculate_sma(prices, length=3)
    assert pd.isna(sma.iloc[0])
    assert sma.iloc[2] == 2.0  # (1+2+3)/3 = 2.0
    assert sma.iloc[4] == 4.0  # (3+4+5)/3 = 4.0

def test_calculate_ema_system():
    df = pd.DataFrame({
        "close": [10.0, 12.0, 11.0, 13.0, 14.0, 15.0] * 10,
        "volume": [100, 200, 150, 300, 250, 400] * 10
    })
    res = calculate_ema_system(df, ema_length=5, ma_type="SMA + Bollinger Bands", ma_length=3)
    assert "ema" in res.columns
    assert "ema_ma" in res.columns
    assert "ema_bb_upper" in res.columns
    assert "ema_bb_lower" in res.columns
