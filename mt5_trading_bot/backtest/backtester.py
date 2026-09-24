import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from ..engine.strategy_engine import StrategyEngine, TradingSignal
from ..risk.risk_manager import RiskManager
from ..config import Config
from ..utils.logger import logger

@dataclass
class BacktestTrade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    volume: float
    pnl: float
    return_pct: float
    reason: str

class Backtester:
    """
    Backtesting Engine for MT5 Historical Data.
    Runs StrategyEngine bar-by-bar and simulates trade lifecycle and risk management.
    """

    def __init__(self, config: Config, initial_balance: float = 10000.0):
        self.config = config
        self.initial_balance = initial_balance
        self.engine = StrategyEngine(
            symbol=config.SYMBOL,
            timeframe=config.TIMEFRAME,
            max_bars=config.MAX_BARS,
            zone_body_pct=config.ZONE_BODY_PCT,
            tap_source=config.TAP_SOURCE,
            stop_on_tap=config.STOP_ON_TAP,
            stop_iss_34_by_wick_tap=config.STOP_ISS_34_BY_WICK_TAP
        )
        self.risk_manager = RiskManager(config)

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run backtest on OHLCV DataFrame."""
        if df is None or df.empty or len(df) < 50:
            logger.error("Insufficient historical data for backtesting.")
            return {}

        df = df.copy().reset_index(drop=True)
        self.engine.reset()

        balance = self.initial_balance
        equity = balance
        equity_curve = [balance]
        trades: List[BacktestTrade] = []

        active_trade: Optional[Dict[str, Any]] = None

        self.risk_manager.reset_daily_stats(balance)

        signals = self.engine.process_data(df)
        signals_by_bar = {sig.bar_index: sig for sig in signals}

        for i in range(1, len(df)):
            row = df.iloc[i]
            h, l, c = float(row["high"]), float(row["low"]), float(row["close"])
            ts = pd.to_datetime(row["time"])
            bar_idx = i

            # 1. Manage active position exit
            if active_trade is not None:
                dir_ = active_trade["direction"]
                sl = active_trade["sl"]
                tp = active_trade["tp"]
                entry = active_trade["entry"]
                vol = active_trade["volume"]

                hit_sl = (l <= sl) if dir_ == "BUY" else (h >= sl)
                hit_tp = (h >= tp) if dir_ == "BUY" else (l <= tp)

                if hit_sl or hit_tp:
                    exit_price = sl if hit_sl else tp
                    pnl_per_unit = (exit_price - entry) if dir_ == "BUY" else (entry - exit_price)
                    pnl = pnl_per_unit * vol * 100.0  # Normalized point value factor

                    balance += pnl
                    equity = balance
                    equity_curve.append(balance)

                    ret_pct = (pnl / balance) * 100.0
                    trades.append(BacktestTrade(
                        entry_time=active_trade["entry_time"],
                        exit_time=ts,
                        symbol=self.config.SYMBOL,
                        direction=dir_,
                        entry_price=entry,
                        exit_price=exit_price,
                        stop_loss=sl,
                        take_profit=tp,
                        volume=vol,
                        pnl=pnl,
                        return_pct=ret_pct,
                        reason="Hit SL" if hit_sl else "Hit TP"
                    ))
                    self.risk_manager.record_trade_result(pnl)
                    active_trade = None

            # 2. Process new signal entry if no position is open
            if active_trade is None and bar_idx in signals_by_bar:
                sig = signals_by_bar[bar_idx]
                approved, reason = self.risk_manager.validate_new_trade(
                    current_balance=balance,
                    current_equity=equity,
                    current_spread_pips=10.0,
                    current_positions_count=0
                )

                if approved:
                    vol = self.risk_manager.calculate_lot_size(
                        balance=balance,
                        entry_price=sig.entry_price,
                        stop_loss=sig.stop_loss
                    )
                    active_trade = {
                        "entry_time": ts,
                        "direction": sig.direction,
                        "entry": sig.entry_price,
                        "sl": sig.stop_loss,
                        "tp": sig.take_profit,
                        "volume": vol
                    }

        # Calculate metrics
        total_trades = len(trades)
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]

        win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)

        # Max drawdown calculation
        eq_arr = np.array(equity_curve)
        peaks = np.maximum.accumulate(eq_arr)
        drawdowns = (peaks - eq_arr) / peaks * 100.0
        max_drawdown = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

        net_profit = balance - self.initial_balance

        results = {
            "initial_balance": self.initial_balance,
            "final_balance": round(balance, 2),
            "net_profit": round(net_profit, 2),
            "return_pct": round((net_profit / self.initial_balance) * 100.0, 2),
            "total_trades": total_trades,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate_pct": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "trades": trades
        }

        self._print_report(results)
        return results

    def _print_report(self, res: Dict[str, Any]):
        """Print clean summary performance report."""
        logger.info("==================================================")
        logger.info("              BACKTEST PERFORMANCE REPORT         ")
        logger.info("==================================================")
        logger.info(f" Initial Balance:  ${res['initial_balance']:.2f}")
        logger.info(f" Final Balance:    ${res['final_balance']:.2f}")
        logger.info(f" Net Profit:       ${res['net_profit']:.2f} ({res['return_pct']}%)")
        logger.info(f" Total Trades:     {res['total_trades']}")
        logger.info(f" Win Rate:         {res['win_rate_pct']}%")
        logger.info(f" Profit Factor:    {res['profit_factor']}")
        logger.info(f" Max Drawdown:     {res['max_drawdown_pct']}%")
        logger.info("==================================================")
