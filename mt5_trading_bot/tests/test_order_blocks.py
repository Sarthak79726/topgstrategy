import pytest
import pandas as pd
from mt5_trading_bot.strategy.state import StrategyState
from mt5_trading_bot.strategy.order_blocks import create_order_block, update_order_blocks

def test_order_block_creation():
    state = StrategyState()
    # Bullish OB search for opposite red candle (close < open)
    df = pd.DataFrame([
        {"open": 100, "high": 101, "low": 98, "close": 99},   # red candle
        {"open": 99, "high": 105, "low": 99, "close": 104}    # current impulse
    ])

    create_order_block(state, df, bar_index=1, is_bullish=True)
    assert len(state.obLevels) == 1
    ob = state.obLevels[0]
    assert ob.bull is True
    assert ob.top == 100.0
    assert ob.bot == 98.0
