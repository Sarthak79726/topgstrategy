from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from ..strategy.strategy import StrategyEngine
from ..signals.signal_generator import SignalGenerator
from ..risk.position_sizing import calculate_position_size
from ..backtest.metrics import calculate_backtest_metrics
from ..utils.logger import logger

class BacktestEngine:
    """
    Sequential bar-by-bar historical backtesting engine using the exact same StrategyEngine
    as live trading, with zero look-ahead bias.
    """

    def __init__(self, config_obj: Any, initial_balance: float = 10000.0,
                 spread_pips: float = 2.0, commission_per_lot: float = 0.0):
        self.config = config_obj
        self.initial_balance = initial_balance
        self.spread_pips = spread_pips
        self.commission_per_lot = commission_per_lot

        self.strategy = StrategyEngine(config_obj)
        self.signal_gen = SignalGenerator(
            symbol=getattr(config_obj, "SYMBOL", "XAUUSD"),
            timeframe=getattr(config_obj, "TIMEFRAME", "M5"),
            default_sl_pips=getattr(config_obj, "DEFAULT_SL_PIPS", 50.0),
            default_tp_pips=getattr(config_obj, "DEFAULT_TP_PIPS", 150.0),
            pip_size=0.1 if "XAU" in getattr(config_obj, "SYMBOL", "XAUUSD") else 0.0001
        )

        self.balance = initial_balance
        self.equity = initial_balance
        self.trades: List[Dict[str, Any]] = []
        self.open_position: Optional[Dict[str, Any]] = None
        self.equity_curve: List[float] = [initial_balance]

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Execute historical backtest over DataFrame sequentially."""
        if df is None or len(df) < 200:
            logger.error("Insufficient DataFrame rows for backtesting.")
            return {}

        logger.info(f"Starting Backtest on {len(df)} candles...")

        for i in range(132, len(df)):
            df_slice = df.iloc[:i+1].copy()
            current_bar = df_slice.iloc[-1]

            r_close = float(current_bar["close"])
            r_high = float(current_bar["high"])
            r_low = float(current_bar["low"])
            r_open = float(current_bar["open"])
            bar_idx = int(current_bar["bar_index"])
            bar_time = current_bar["time"]

            # 1. Check open position SL / TP hit
            if self.open_position is not None:
                pos = self.open_position
                closed = False
                exit_price = 0.0
                profit = 0.0

                if pos["direction"] == "BUY":
                    # Check SL hit
                    if r_low <= pos["sl"]:
                        exit_price = pos["sl"]
                        closed = True
                        pips = (exit_price - pos["entry"]) / self.signal_gen.pip_size
                        profit = pips * 10.0 * pos["volume"]
                    # Check TP hit
                    elif r_high >= pos["tp"]:
                        exit_price = pos["tp"]
                        closed = True
                        pips = (exit_price - pos["entry"]) / self.signal_gen.pip_size
                        profit = pips * 10.0 * pos["volume"]

                elif pos["direction"] == "SELL":
                    # Check SL hit
                    if r_high >= pos["sl"]:
                        exit_price = pos["sl"]
                        closed = True
                        pips = (pos["entry"] - exit_price) / self.signal_gen.pip_size
                        profit = pips * 10.0 * pos["volume"]
                    # Check TP hit
                    elif r_low <= pos["tp"]:
                        exit_price = pos["tp"]
                        closed = True
                        pips = (pos["entry"] - exit_price) / self.signal_gen.pip_size
                        profit = pips * 10.0 * pos["volume"]

                if closed:
                    # Subtract spread & commission
                    spread_cost = self.spread_pips * 10.0 * pos["volume"]
                    comm_cost = self.commission_per_lot * pos["volume"]
                    profit = profit - spread_cost - comm_cost

                    self.balance += profit
                    self.equity = self.balance

                    pos["exit_bar"] = bar_idx
                    pos["exit_time"] = bar_time
                    pos["exit_price"] = exit_price
                    pos["profit"] = profit
                    self.trades.append(pos)
                    self.open_position = None

            # 2. Process bar in strategy engine
            events = self.strategy.process_bar(df_slice, bar_idx)

            # 3. Generate Signal if no open position
            if self.open_position is None:
                sig = self.signal_gen.generate_signal(self.strategy.state, events, df_slice, bar_idx, self.strategy.tap_source)
                if sig is not None and sig.direction != "NO_TRADE":
                    # Position sizing
                    volume = calculate_position_size(self.equity, getattr(self.config, "RISK_PERCENT", 1.0),
                                                     sig.entry_price, sig.stop_loss, self.signal_gen.pip_size)

                    self.open_position = {
                        "ticket": len(self.trades) + 1,
                        "entry_bar": bar_idx,
                        "entry_time": bar_time,
                        "direction": sig.direction,
                        "volume": volume,
                        "entry": sig.entry_price,
                        "sl": sig.stop_loss,
                        "tp": sig.take_profit,
                        "component": sig.strategy_component
                    }

            self.equity_curve.append(self.equity)

        metrics = calculate_backtest_metrics(self.trades, self.initial_balance)
        logger.info(f"Backtest Complete. Total Trades: {metrics['total_trades']}, Win Rate: {metrics['win_rate_pct']}%, Net Profit: ${metrics['net_profit']}")
        return {
            "metrics": metrics,
            "trades": self.trades,
            "equity_curve": self.equity_curve
        }
