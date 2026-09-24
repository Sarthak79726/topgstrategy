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
