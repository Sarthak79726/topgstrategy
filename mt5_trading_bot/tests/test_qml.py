import pytest
from mt5_trading_bot.strategy.state import StrategyState, Level
from mt5_trading_bot.strategy.levels import promote_last_choch_levels_to_best

def test_qml_promotion():
    state = StrategyState()
    # Add a QML level kind=7 with left=10
    qml_lv = Level(left=10, right=20, top=100.0, bot=95.0, col="purple", txt="SELL QML",
                   kind=7, dir=1, active=True, deleted=False, bornBar=10)
    state.levels.append(qml_lv)

    promote_last_choch_levels_to_best(state.levels, qml_left=10, bar_index=30)
    assert qml_lv.deleted is True
    # Best level kind=8 should be appended
    best_lvs = [l for l in state.levels if l.kind == 8]
    assert len(best_lvs) == 1
    assert best_lvs[0].txt == "D-CHOCH SELL QML"
