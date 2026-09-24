import pytest
import pandas as pd
from mt5_trading_bot.strategy.state import StrategyState, Level
from mt5_trading_bot.signals.signal_generator import SignalGenerator
from mt5_trading_bot.signals.signal import Signal

def test_signal_generation():
    sig_gen = SignalGenerator(symbol="XAUUSD", timeframe="M5")
    state = StrategyState()
    state.trend = 1

    # Add active Level tapped by current candle
    lv = Level(left=5, right=10, top=2005.0, bot=1995.0, col="green", txt="BUY TJL1",
               kind=1, dir=1, active=True, deleted=False, bornBar=5)
    state.levels.append(lv)

    df = pd.DataFrame([
        {"open": 2002.0, "high": 2004.0, "low": 1998.0, "close": 2000.0} # candle taps 1995-2005
    ])

    sig = sig_gen.generate_signal(state, events=[], df=df, bar_index=10)
    assert sig is not None
    assert sig.direction == "BUY"
    assert sig.strategy_component == "BUY TJL1_TAP"
    assert sig.signal_id != ""
