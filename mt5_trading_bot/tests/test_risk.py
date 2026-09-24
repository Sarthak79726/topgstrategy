from mt5_trading_bot.config import Config
from mt5_trading_bot.risk.risk_manager import RiskManager

def test_position_size():
    cfg = Config(RISK_PERCENT=1.0)
    rm = RiskManager(cfg)
    vol = rm.calculate_lot_size(balance=10000.0, entry_price=2000.0, stop_loss=1990.0)
    assert vol >= 0.01

def test_risk_manager_controls():
    cfg = Config(MAX_SPREAD=30.0, MAX_POSITIONS=1, MAX_DAILY_LOSS_PERCENT=5.0)
    rm = RiskManager(cfg)

    # 1. Allowed test
    allowed, reason = rm.validate_new_trade(current_balance=10000.0, current_equity=10000.0, current_spread_pips=10.0, current_positions_count=0)
    assert allowed is True

    # 2. Spread violation
    allowed, reason = rm.validate_new_trade(current_balance=10000.0, current_equity=10000.0, current_spread_pips=35.0, current_positions_count=0)
    assert allowed is False
    assert "spread" in reason.lower()

    # 3. Max positions violation
    allowed, reason = rm.validate_new_trade(current_balance=10000.0, current_equity=10000.0, current_spread_pips=10.0, current_positions_count=1)
    assert allowed is False
    assert "positions" in reason.lower()
