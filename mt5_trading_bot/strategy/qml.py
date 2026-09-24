from typing import Optional
from .state import StrategyState, Level
from .levels import promote_last_choch_levels_to_best

def handle_qml_on_choch(state: StrategyState, is_bullish: bool, bar_index: int,
                        dual_choch_hit: bool):
    """
    Handle QML level creation or Dual-CHOCH level promotion.
    """
    if dual_choch_hit:
        promote_last_choch_levels_to_best(state.levels, state.lastQmlLeft, bar_index)
