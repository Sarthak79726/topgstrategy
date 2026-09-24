import pytest
import pandas as pd
from mt5_trading_bot.strategy.state import StrategyState
from mt5_trading_bot.strategy.fvg import update_fvg

def test_fvg_detection():
    state = StrategyState()
    # Bullish FVG: low > high[2]
    df = pd.DataFrame([
        {"open": 100, "high": 102, "low": 99, "close": 101},  # bar 0
        {"open": 102, "high": 105, "low": 101, "close": 104}, # bar 1
        {"open": 105, "high": 108, "low": 104, "close": 107}  # bar 2: low(104) > high[0](102)
    ])

    update_fvg(state, df, bar_index=2, show_fvg=True)
    assert len(state.fvgLevels) == 1
    fv = state.fvgLevels[0]
    assert fv.bull is True
    assert fv.top == 104.0
    assert fv.bot == 102.0
