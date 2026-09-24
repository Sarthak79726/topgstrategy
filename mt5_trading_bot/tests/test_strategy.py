import pytest
import pandas as pd
import numpy as np
from mt5_trading_bot.strategy.candles import candle_zone, is_tapped
from mt5_trading_bot.strategy.ema import calculate_ema
from mt5_trading_bot.strategy.levels import level_dir

def test_candle_zone():
    top, bot = candle_zone(o=100.0, c=110.0, h=115.0, l=95.0, is_high=True, zone_body_pct=1.0)
    assert top == 115.0
    assert round(bot, 1) == 109.9  # body_top(110) - 10*0.01 = 109.9

    top2, bot2 = candle_zone(o=100.0, c=110.0, h=115.0, l=95.0, is_high=False, zone_body_pct=1.0)
    assert top2 == 100.1
    assert bot2 == 95.0

def test_is_tapped():
    tapped_wick = is_tapped(r_close=105.0, r_high=112.0, r_low=98.0, top_=110.0, bot_=100.0, tap_source="TapByWick")
    assert tapped_wick is True

    tapped_close = is_tapped(r_close=105.0, r_high=112.0, r_low=98.0, top_=110.0, bot_=100.0, tap_source="TapByClose")
    assert tapped_close is True

def test_ema_calculation():
    s = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0])
    ema = calculate_ema(s, length=5)
    assert len(ema) == len(s)
    assert not np.isnan(ema.iloc[-1])

def test_level_direction():
    assert level_dir(kind=1, is_high=True) == 1
    assert level_dir(kind=1, is_high=False) == -1
    assert level_dir(kind=3, is_high=False) == -1
    assert level_dir(kind=4, is_high=True) == 1
