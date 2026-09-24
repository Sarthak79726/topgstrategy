from typing import Tuple
from .state import StrategyState, Level
from .levels import add_level, delete_latest_tjl1_by_left

def process_tjl_on_bos(state: StrategyState, is_bullish: bool, bar_index: int,
                       df_slice: float, zone_body_pct: float = 1.0):
    """
    Generate TJL1 and TJL2 levels on BOS event.
    """
    if is_bullish:
        state.tjl1 = state.lastCH
        state.tjl2 = state.lastCL
        state.tjl1Set = True
        state.issOrTjlSinceChoch = True
    else:
        state.tjl1 = state.lastCL
        state.tjl2 = state.lastCH
        state.tjl1Set = True
        state.issOrTjlSinceChoch = True
