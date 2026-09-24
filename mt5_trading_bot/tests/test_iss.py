import pytest
import pandas as pd
from mt5_trading_bot.strategy.state import StrategyState
from mt5_trading_bot.strategy.iss import update_iss_state, reset_bull_iss, reset_bear_iss

def test_iss_resets():
    state = StrategyState()
    state.bullIssState = 2
    state.bullIssBaseLow = 100.0
    reset_bull_iss(state)
    assert state.bullIssState == 0
    assert state.bullIssBaseLow is None

def test_iss_invalidation():
    state = StrategyState()
    state.bullIssState = 2
    state.bullIssBaseLow = 100.0

    df = pd.DataFrame([{"bar_index": 1, "open": 105, "high": 106, "low": 95, "close": 94}])
    # Close < bullIssBaseLow (94 < 100) -> invalidation
    event = update_iss_state(state, bar_index=1, open_c=105, close_c=94, high_c=106, low_c=95,
                             bullish_shift=False, bearish_shift=True, df=df, enable_iss=True)
    assert state.bullIssState == 0
    assert event is None
