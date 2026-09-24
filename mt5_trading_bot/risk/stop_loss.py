def calculate_stop_loss(direction: str, entry_price: float, level_boundary: float,
                        buffer_pips: float = 10.0, pip_size: float = 0.1) -> float:
    """Calculate stop loss price based on level boundary + buffer."""
    buffer = buffer_pips * pip_size
    if direction.upper() == "BUY":
        return min(level_boundary, entry_price) - buffer
    else:
        return max(level_boundary, entry_price) + buffer
