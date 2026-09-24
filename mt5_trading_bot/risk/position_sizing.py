import math
from typing import Optional
from ..mt5.symbols import SymbolManager

def calculate_position_size(equity: float, risk_percent: float, entry_price: float,
                            stop_loss: float, pip_size: float = 0.1,
                            symbol_manager: Optional[SymbolManager] = None) -> float:
    """
    Calculate risk-based lot size normalized to broker volume constraints.
    Formula: Risk Amount = Equity * (Risk % / 100)
             SL Pips = |Entry - SL| / Pip Size
             Raw Lots = Risk Amount / (SL Pips * Pip Value per lot)
    """
    if equity <= 0 or risk_percent <= 0:
        return 0.01

    sl_distance = abs(entry_price - stop_loss)
    if sl_distance <= 0:
        return 0.01

    sl_pips = sl_distance / pip_size
    if sl_pips <= 0:
        return 0.01

    risk_amount = equity * (risk_percent / 100.0)

    # Estimate pip value per standard lot (approx $10 per pip for Forex, $10 for Gold 0.1 pip)
    pip_value_per_lot = 10.0

    raw_volume = risk_amount / (sl_pips * pip_value_per_lot)

    if symbol_manager is not None:
        return symbol_manager.normalize_volume(raw_volume)

    # Fallback normalization (min 0.01, step 0.01)
    norm_vol = max(0.01, round(raw_volume, 2))
    return norm_vol
