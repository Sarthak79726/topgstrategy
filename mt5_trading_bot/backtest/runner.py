import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from .engine import BacktestEngine
from ..config import config
from ..utils.logger import logger

def run_backtest_cli(df: pd.DataFrame, plot_chart: bool = True):
    """Run backtest from CLI and optional equity curve chart rendering."""
    engine = BacktestEngine(config, initial_balance=10000.0)
    results = engine.run(df)

    metrics = results.get("metrics", {})
    trades = results.get("trades", [])

    print("\n" + "=" * 50)
    print("           BACKTEST RESULTS SUMMARY")
    print("=" * 50)
    for k, v in metrics.items():
        print(f"  {k.replace('_', ' ').title():<25}: {v}")
    print("=" * 50 + "\n")

    # Export trades to CSV
    if trades:
        trades_df = pd.DataFrame(trades)
        export_path = Path(__file__).parent.parent / "logs" / "backtest_trades.csv"
        trades_df.to_csv(export_path, index=False)
        logger.info(f"Backtest trade log exported to {export_path}")

    # Plot Equity Curve
    if plot_chart and "equity_curve" in results:
        plt.figure(figsize=(12, 6))
        plt.plot(results["equity_curve"], label="Equity ($)", color="#00ffcc", linewidth=1.5)
        plt.title(f"Backtest Equity Curve - {config.SYMBOL} ({config.TIMEFRAME})", fontsize=14)
        plt.xlabel("Candles Processed")
        plt.ylabel("Account Equity ($)")
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.legend()

        chart_path = Path(__file__).parent.parent / "logs" / "equity_curve.png"
        plt.savefig(chart_path, dpi=300, bbox_inches="tight")
        logger.info(f"Equity curve chart saved to {chart_path}")
        plt.close()

    return results
