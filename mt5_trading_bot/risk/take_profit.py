def calculate_take_profit(direction: str, entry_price: float, sl_price: float,
                          rr_ratio: float = 3.0, default_tp_pips: float = 150.0,
                          pip_size: float = 0.1) -> float:
    """Calculate take profit price based on Risk-Reward Ratio or default pips."""
    sl_distance = abs(entry_price - sl_price)
    tp_distance = sl_distance * rr_ratio if sl_distance > 0 else (default_tp_pips * pip_size)

    if direction.upper() == "BUY":
        return entry_price + tp_distance
    else:
        return entry_price - tp_distance
