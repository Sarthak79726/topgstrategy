import math
import pandas as pd
import numpy as np
from typing import List, Dict, Any

def calculate_backtest_metrics(trades: List[Dict[str, Any]], initial_balance: float = 10000.0) -> Dict[str, Any]:
    """
    Calculate comprehensive backtest statistics:
    - Total Trades, Win Rate, Profit Factor, Expectancy
    - Max Drawdown %, Max Consecutive Losses, Avg Win, Avg Loss
    """
    if not trades:
        return {
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "net_profit": 0.0,
            "max_drawdown_pct": 0.0,
            "expectancy": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "max_consecutive_losses": 0
        }

    df_trades = pd.DataFrame(trades)
    total_trades = len(df_trades)
    profits = df_trades["profit"].values

    wins = profits[profits > 0]
    losses = profits[profits < 0]

    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total_trades) * 100.0 if total_trades > 0 else 0.0

    gross_profit = float(np.sum(wins)) if len(wins) > 0 else 0.0
    gross_loss = float(np.abs(np.sum(losses))) if len(losses) > 0 else 0.0

    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
    net_profit = float(np.sum(profits))

    avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
    avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.0
    expectancy = (win_rate / 100.0 * avg_win) + ((1.0 - win_rate / 100.0) * avg_loss)

    # Max Drawdown %
    equity_curve = initial_balance + np.cumsum(profits)
    peak = np.maximum.accumulate(np.insert(equity_curve, 0, initial_balance))
    drawdowns = (peak[1:] - equity_curve) / peak[1:] * 100.0
    max_drawdown = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

    # Max Consecutive Losses
    max_cons_losses = 0
    curr_cons = 0
    for p in profits:
        if p < 0:
            curr_cons += 1
            max_cons_losses = max(max_cons_losses, curr_cons)
        else:
            curr_cons = 0

    return {
        "total_trades": total_trades,
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
        "net_profit": round(net_profit, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "expectancy": round(expectancy, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "max_consecutive_losses": max_cons_losses
    }
