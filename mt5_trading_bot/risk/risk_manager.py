from typing import Tuple, Dict, Any, Optional
from ..config import Config
from ..utils.logger import logger

class RiskManager:
    """
    Enforces risk control policies, position sizing, spread checks, daily loss limits,
    and consecutive loss safeguards.
    """

    def __init__(self, config: Config):
        self.config = config
        self.daily_starting_balance: Optional[float] = None
        self.trades_today_count: int = 0
        self.consecutive_losses: int = 0

    def reset_daily_stats(self, balance: float):
        """Reset daily tracking metrics at market day start."""
        self.daily_starting_balance = balance
        self.trades_today_count = 0
        self.consecutive_losses = 0

    def calculate_lot_size(self, balance: float, entry_price: float, stop_loss: float,
                           point_size: float = 0.01, tick_value: float = 1.0,
                           min_lot: float = 0.01, max_lot: float = 100.0, lot_step: float = 0.01) -> float:
        """
        Calculate broker-valid position volume based on risk percentage and SL distance.
        """
        sl_distance = abs(entry_price - stop_loss)
        if sl_distance <= 0:
            return min_lot

        risk_amount = balance * (self.config.RISK_PERCENT / 100.0)

        # Risk formula: lot_size = risk_amount / (sl_points * tick_value_per_lot)
        sl_points = sl_distance / point_size if point_size > 0 else sl_distance
        raw_lots = risk_amount / (sl_points * tick_value) if (sl_points * tick_value) > 0 else min_lot

        # Normalize to lot steps and boundaries
        lots = round(raw_lots / lot_step) * lot_step
        lots = max(min_lot, min(max_lot, lots))
        return round(lots, 2)

    def validate_new_trade(self, current_balance: float, current_equity: float,
                           current_spread_pips: float, current_positions_count: int) -> Tuple[bool, str]:
        """
        Validate all risk rules prior to taking a trade.
        """
        # 1. Spread filter
        if current_spread_pips > self.config.MAX_SPREAD:
            return False, f"Spread ({current_spread_pips:.1f}) exceeds maximum allowed ({self.config.MAX_SPREAD})"

        # 2. Maximum open positions limit
        if current_positions_count >= self.config.MAX_POSITIONS:
            return False, f"Open positions ({current_positions_count}) reached maximum limit ({self.config.MAX_POSITIONS})"

        # 3. Daily trades count limit
        if self.trades_today_count >= self.config.MAX_TRADES_PER_DAY:
            return False, f"Daily trade limit ({self.config.MAX_TRADES_PER_DAY}) reached"

        # 4. Consecutive loss limit
        if self.consecutive_losses >= self.config.MAX_CONSECUTIVE_LOSSES:
            return False, f"Consecutive loss limit ({self.config.MAX_CONSECUTIVE_LOSSES}) hit"

        # 5. Daily loss percentage check
        if self.daily_starting_balance is not None and self.daily_starting_balance > 0:
            drawdown_pct = ((self.daily_starting_balance - current_equity) / self.daily_starting_balance) * 100.0
            if drawdown_pct >= self.config.MAX_DAILY_LOSS_PERCENT:
                return False, f"Daily drawdown ({drawdown_pct:.2f}%) exceeded max limit ({self.config.MAX_DAILY_LOSS_PERCENT}%)"

        return True, "Trade approved by RiskManager"

    def record_trade_result(self, profit: float):
        """Update trade counters based on trade outcome."""
        self.trades_today_count += 1
        if profit < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
