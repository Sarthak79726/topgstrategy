from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime, timezone

@dataclass
class Signal:
    symbol: str
    timeframe: str
    bar_index: int
    direction: str  # BUY, SELL, NO_TRADE
    entry_price: float
    stop_loss: float
    take_profit: float
    strategy_component: str  # e.g., TJL1_TAP, QML_TAP, ISS4_CONFIRMED, CHOCH_REVERSAL
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    reason: str = ""
    confidence_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def signal_id(self) -> str:
        """Generate unique signal identifier to prevent duplicate executions."""
        return f"{self.symbol}_{self.timeframe}_{self.bar_index}_{self.direction}_{self.strategy_component}"
