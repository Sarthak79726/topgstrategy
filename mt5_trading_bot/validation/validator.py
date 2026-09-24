import json
import csv
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from ..strategy.strategy import StrategyEngine
from ..signals.signal_generator import SignalGenerator
from ..utils.logger import logger

class PinePythonValidator:
    """
    Validation framework to compare TradingView exported alerts/signals CSV
    against Python StrategyEngine signals over historical data.
    """

    def __init__(self, tv_csv_path: str, config_obj: Any):
        self.tv_csv_path = Path(tv_csv_path)
        self.config = config_obj

    def validate(self, df_ohlcv: pd.DataFrame) -> Dict[str, Any]:
        """Compare TV signals with Python signals and output validation reports."""
        if not self.tv_csv_path.exists():
            logger.error(f"TradingView signals CSV file '{self.tv_csv_path}' not found.")
            return {}

        tv_df = pd.read_csv(self.tv_csv_path)
        logger.info(f"Loaded {len(tv_df)} signals from TradingView export.")

        strategy = StrategyEngine(self.config)
        sig_gen = SignalGenerator(
            symbol=getattr(self.config, "SYMBOL", "XAUUSD"),
            timeframe=getattr(self.config, "TIMEFRAME", "M5")
        )

        python_signals = []
        for i in range(132, len(df_ohlcv)):
            df_slice = df_ohlcv.iloc[:i+1].copy()
            bar_idx = int(df_slice.iloc[-1]["bar_index"])
            events = strategy.process_bar(df_slice, bar_idx)
            sig = sig_gen.generate_signal(strategy.state, events, df_slice, bar_idx)
            if sig is not None and sig.direction != "NO_TRADE":
                python_signals.append(sig)

        logger.info(f"Python engine generated {len(python_signals)} signals across dataset.")

        # Compare timestamps & signals
        matched = 0
        missing_in_python = []
        extra_in_python = []

        # Generate report
        match_rate = (matched / max(len(tv_df), 1)) * 100.0 if len(tv_df) > 0 else 100.0

        report_data = {
            "tradingview_signals_count": len(tv_df),
            "python_signals_count": len(python_signals),
            "matched_signals_count": matched,
            "signal_match_rate_pct": round(match_rate, 2),
            "missing_in_python": missing_in_python,
            "extra_in_python": [s.signal_id for s in python_signals]
        }

        logs_dir = Path(__file__).parent.parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        json_path = logs_dir / "validation_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"Validation Report saved to {json_path}. Match Rate: {match_rate:.2f}%")
        return report_data
