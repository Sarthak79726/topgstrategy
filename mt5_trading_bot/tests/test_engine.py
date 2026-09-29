import pytest
import pandas as pd
import numpy as np
from mt5_trading_bot.engine.strategy_engine import StrategyEngine

def test_engine_processing():
    dates = pd.date_range("2026-01-01", periods=100, freq="5min")
    np.random.seed(42)
    close_prices = 2000.0 + np.cumsum(np.random.randn(100) * 0.5)

    df = pd.DataFrame({
        "time": dates,
        "open": close_prices - 0.2,
        "high": close_prices + 0.5,
        "low": close_prices - 0.5,
        "close": close_prices
    })

    engine = StrategyEngine(symbol="XAUUSD", timeframe="M5")
    signals = engine.process_data(df)
    assert isinstance(signals, list)
    assert engine.state.trend in (-1, 0, 1)

def test_engine_level_tap_signal():
    dates = pd.date_range("2026-01-01", periods=10, freq="5min")
    df = pd.DataFrame({
        "time": dates,
        "open":  [2000.0, 2010.0, 2005.0, 1990.0, 1995.0, 2005.0, 2000.0, 1998.0, 2002.0, 2000.0],
        "high":  [2012.0, 2015.0, 2008.0, 1995.0, 2008.0, 2010.0, 2005.0, 2002.0, 2005.0, 2005.0],
        "low":   [1998.0, 2004.0, 1988.0, 1985.0, 1990.0, 1998.0, 1995.0, 1992.0, 1998.0, 1995.0],
        "close": [2010.0, 2005.0, 1990.0, 1992.0, 2005.0, 2000.0, 1998.0, 2000.0, 2003.0, 2001.0]
    })

    engine = StrategyEngine(symbol="XAUUSD", timeframe="M5")
    signals = engine.process_data(df)
    assert isinstance(signals, list)

