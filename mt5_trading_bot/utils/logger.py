import os
import logging
import csv
from pathlib import Path
from typing import Any, Dict

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

BOT_LOG_PATH = LOGS_DIR / "bot.log"
SIGNALS_CSV_PATH = LOGS_DIR / "signals.csv"
TRADES_CSV_PATH = LOGS_DIR / "trades.csv"
ERRORS_LOG_PATH = LOGS_DIR / "errors.log"

def setup_logger(name: str = "MT5Bot", log_level: str = "INFO", debug: bool = True) -> logging.Logger:
    logger = logging.getLogger(name)
    level = logging.DEBUG if debug else getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    if not logger.handlers:
        # Console Handler
        c_handler = logging.StreamHandler()
        c_handler.setLevel(level)
        c_format = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        c_handler.setFormatter(c_format)
        logger.addHandler(c_handler)

        # File Handler (bot.log)
        f_handler = logging.FileHandler(BOT_LOG_PATH, encoding="utf-8")
        f_handler.setLevel(level)
        f_handler.setFormatter(c_format)
        logger.addHandler(f_handler)

        # Error File Handler (errors.log)
        err_handler = logging.FileHandler(ERRORS_LOG_PATH, encoding="utf-8")
        err_handler.setLevel(logging.ERROR)
        err_handler.setFormatter(c_format)
        logger.addHandler(err_handler)

    return logger

logger = setup_logger()

def log_signal_to_csv(signal_dict: Dict[str, Any]):
    """Log structured signal to logs/signals.csv."""
    file_exists = SIGNALS_CSV_PATH.exists()
    fieldnames = ["timestamp", "symbol", "timeframe", "signal_id", "direction", "entry", "stop_loss", "take_profit", "strategy_component", "reason"]
    with open(SIGNALS_CSV_PATH, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: signal_dict.get(k, "") for k in fieldnames})

def log_trade_to_csv(trade_dict: Dict[str, Any]):
    """Log trade execution result to logs/trades.csv."""
    file_exists = TRADES_CSV_PATH.exists()
    fieldnames = ["timestamp", "symbol", "ticket", "order_type", "volume", "price", "sl", "tp", "retcode", "result_comment"]
    with open(TRADES_CSV_PATH, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: trade_dict.get(k, "") for k in fieldnames})
