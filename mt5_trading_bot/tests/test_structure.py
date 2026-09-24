import pytest
from mt5_trading_bot.strategy.candles import candle_zone, is_tapped
from mt5_trading_bot.strategy.levels import level_dir, level_display_text

def test_candle_zone():
    top, bot = candle_zone(o=100.0, c=110.0, h=115.0, l=95.0, is_high=True, zone_body_pct=1.0)
    assert top == 115.0
    # pad = 10 * 1% = 0.1, body_top = 110, bot = 110 - 0.1 = 109.9
    assert bot == pytest.approx(109.9)

def test_tap_detection():
    # Tap by Wick
    assert is_tapped(r_close=100.0, r_high=105.0, r_low=98.0, top_=102.0, bot_=99.0, tap_source="TapByWick") is True
    assert is_tapped(r_close=100.0, r_high=95.0, r_low=90.0, top_=102.0, bot_=99.0, tap_source="TapByWick") is False

    # Tap by Close
    assert is_tapped(r_close=100.0, r_high=105.0, r_low=98.0, top_=102.0, bot_=99.0, tap_source="TapByClose") is True
    assert is_tapped(r_close=105.0, r_high=105.0, r_low=98.0, top_=102.0, bot_=99.0, tap_source="TapByClose") is False

def test_level_directions():
    assert level_dir(1, is_high=True) == 1
    assert level_dir(1, is_high=False) == -1
    assert level_dir(3, is_high=False) == -1  # SBR
    assert level_dir(4, is_high=True) == 1   # RBS
