import pytest
from mt5_trading_bot.strategy.bos_choch import detect_structure_shifts

def test_structure_shifts():
    # Bullish Shift: prev green, curr green, close > high[1]
    bull_shift, bear_shift = detect_structure_shifts(
        open_c=100.0, close_c=105.0, high_c=106.0, low_c=99.0,
        open_p=96.0, close_p=98.0, high_p=99.0, low_p=95.0
    )
    assert bull_shift is True
    assert bear_shift is False

    # Bearish Shift: prev red, curr red, close < low[1]
    bull_shift, bear_shift = detect_structure_shifts(
        open_c=96.0, close_c=90.0, high_c=97.0, low_c=89.0,
        open_p=100.0, close_p=95.0, high_p=101.0, low_p=94.0
    )
    assert bull_shift is False
    assert bear_shift is True
