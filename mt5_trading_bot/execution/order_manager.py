from typing import Optional, Dict, Any
from ..mt5.execution import OrderExecutionManager
from ..utils.logger import logger

class OrderManager:
    """Low-level order placement and validation with retry capabilities."""

    def __init__(self, mt5_exec: OrderExecutionManager, max_retries: int = 3):
        self.mt5_exec = mt5_exec
        self.max_retries = max_retries

    def execute_order(self, symbol: str, order_type: str, volume: float, price: float,
                      sl: float, tp: float, comment: str = "JaduTona Bot") -> Optional[Dict[str, Any]]:
        """Attempt order placement with retry logic upon transient MT5 errors."""
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Order Execution Attempt {attempt}/{self.max_retries}...")
            result = self.mt5_exec.send_order(symbol, order_type, volume, price, sl, tp, comment)
            if result is not None and result.get("retcode") in (10009, 10008):  # DONE or PLACED
                return result
            logger.warning(f"Attempt {attempt} failed. Retrying...")

        logger.error("All order placement retries exhausted.")
        return None
