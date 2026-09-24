import pytest
from mt5_trading_bot.strategy.state import StrategyState, Snap
from mt5_trading_bot.strategy.tjl import process_tjl_on_bos

def test_tjl_process():
    state = StrategyState()
    state.lastCH = Snap(bar=10, lvl=100.0)
    state.lastCL = Snap(bar=5, lvl=90.0)

    process_tjl_on_bos(state, is_bullish=True, bar_index=15, df_slice=None)
    assert state.tjl1Set is True
    assert state.tjl1.bar == 10
    assert state.tjl2.bar == 5
    assert state.issOrTjlSinceChoch is True
