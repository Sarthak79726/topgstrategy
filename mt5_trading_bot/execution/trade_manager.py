from typing import Optional, Dict, Any
from ..signals.signal import Signal
from ..risk.risk_manager import RiskManager
from ..risk.position_sizing import calculate_position_size
from ..mt5.execution import OrderExecutionManager
from ..mt5.symbols import SymbolManager
from ..mt5.account import AccountManager
from ..utils.logger import logger

class TradeManager:
    """High-level trade manager orchestrating signal validation, risk checks, sizing, paper mode, and live MT5 execution."""

    def __init__(self, risk_manager: RiskManager, mt5_exec: OrderExecutionManager,
                 symbol_manager: SymbolManager, enable_trading: bool = False,
                 paper_mode: bool = True, risk_percent: float = 1.0):
        self.risk_manager = risk_manager
        self.mt5_exec = mt5_exec
        self.symbol_manager = symbol_manager
        self.enable_trading = enable_trading
        self.paper_mode = paper_mode
        self.risk_percent = risk_percent
        self.paper_positions: list = []

    def handle_signal(self, signal: Signal, current_spread_pips: float = 0.0) -> Optional[Dict[str, Any]]:
        """Process signal, perform pre-trade safety checks, compute lot size, and place trade."""
        if signal is None or signal.direction == "NO_TRADE":
            return None

        # 1. Fetch equity & open positions
        equity = AccountManager.get_equity()
        open_positions = self.mt5_exec.get_open_positions(signal.symbol)
        pos_count = len(open_positions) + len(self.paper_positions if self.paper_mode else [])

        # 2. Risk Checks
        allowed, reason = self.risk_manager.is_trade_allowed(current_spread_pips, pos_count, equity)
        if not allowed:
            logger.warning(f"Trade blocked by RiskManager: {reason}")
            return None

        # 3. Position Sizing
        pip_size = self.symbol_manager.get_pip_size(signal.symbol)
        volume = calculate_position_size(equity, self.risk_percent, signal.entry_price,
                                         signal.stop_loss, pip_size, self.symbol_manager)

        logger.info(f"Trade Pre-Validation Success: {signal.direction} {volume} Lots on {signal.symbol} (Equity: ${equity:.2f}, SL Pips: {abs(signal.entry_price - signal.stop_loss)/pip_size:.1f})")

        # 4. Check Execution Mode
        acc_info = AccountManager.get_account_info() or {}
        acc_num = acc_info.get("login", "5056283582")
        acc_srv = acc_info.get("company", "MetaQuotes-Demo")
        risk_amount = equity * (self.risk_percent / 100.0)

        if self.paper_mode or getattr(self.mt5_exec, "dry_run", True) or not self.enable_trading:
            logger.info("")
            logger.info("==================================================================")
            logger.info("[DRY RUN]")
            logger.info(f"Account:         {acc_num}")
            logger.info(f"Server:          {acc_srv}")
            logger.info(f"Symbol:          {signal.symbol}")
            logger.info(f"Timeframe:       M5")
            logger.info(f"Signal:          {signal.direction}")
            logger.info(f"Entry:           {signal.entry_price:.5f}")
            logger.info(f"Stop Loss:       {signal.stop_loss:.5f}")
            logger.info(f"Take Profit:     {signal.take_profit:.5f}")
            logger.info(f"Lot Size:        {volume:.2f}")
            logger.info(f"Risk:            ${risk_amount:.2f} ({self.risk_percent}%)")
            logger.info("Order execution: SKIPPED - DRY RUN")
            logger.info("==================================================================")
            logger.info("")

            paper_trade = {
                "ticket": 9000000 + len(self.paper_positions) + 1,
                "symbol": signal.symbol,
                "direction": signal.direction,
                "volume": volume,
                "entry": signal.entry_price,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "status": "PAPER_OPEN"
            }
            self.paper_positions.append(paper_trade)
            return paper_trade

        # 5. Live Execution Mode
        logger.info(f"[LIVE MODE] Placing Real Market Order on MT5...")
        result = self.mt5_exec.send_order(
            symbol=signal.symbol,
            order_type=signal.direction,
            volume=volume,
            price=signal.entry_price,
            sl=signal.stop_loss,
            tp=signal.take_profit,
            comment=f"JaduTona {signal.strategy_component}"
        )
        return result
