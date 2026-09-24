import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env if present
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Config(BaseModel):
    # MT5 Account & Connection
    MT5_LOGIN: int = Field(default_factory=lambda: int(os.getenv("MT5_LOGIN", "0")))
    MT5_PASSWORD: str = Field(default_factory=lambda: os.getenv("MT5_PASSWORD", ""))
    MT5_SERVER: str = Field(default_factory=lambda: os.getenv("MT5_SERVER", ""))
    MT5_PATH: str = Field(default_factory=lambda: os.getenv("MT5_PATH", ""))
    MT5_TIMEOUT: int = Field(default_factory=lambda: int(os.getenv("MT5_TIMEOUT", "120000")))
    EXPECTED_MT5_ACCOUNT: int = Field(default_factory=lambda: int(os.getenv("EXPECTED_MT5_ACCOUNT", os.getenv("MT5_LOGIN", "0"))))
    EXPECTED_MT5_SERVER: str = Field(default_factory=lambda: os.getenv("EXPECTED_MT5_SERVER", os.getenv("MT5_SERVER", "")))

    # Market Data
    SYMBOL: str = Field(default_factory=lambda: os.getenv("SYMBOL", "XAUUSD"))
    TIMEFRAME: str = Field(default_factory=lambda: os.getenv("TIMEFRAME", "M5"))
    MAX_BARS: int = Field(default_factory=lambda: int(os.getenv("MAX_BARS", "12000")))

    # Safety Controls
    ENABLE_TRADING: bool = Field(default_factory=lambda: os.getenv("ENABLE_TRADING", "false").lower() == "true")
    ENABLE_ALERTS: bool = Field(default_factory=lambda: os.getenv("ENABLE_ALERTS", "true").lower() == "true")
    PAPER_MODE: bool = Field(default_factory=lambda: os.getenv("PAPER_MODE", "true").lower() == "true")
    DRY_RUN: bool = Field(default_factory=lambda: os.getenv("DRY_RUN", "true").lower() == "true")

    # Risk Settings
    MAGIC_NUMBER: int = Field(default_factory=lambda: int(os.getenv("MAGIC_NUMBER", "26091901")))
    RISK_PERCENT: float = Field(default_factory=lambda: float(os.getenv("RISK_PERCENT", "1.0")))
    MAX_SPREAD: float = Field(default_factory=lambda: float(os.getenv("MAX_SPREAD", "30.0")))
    MAX_POSITIONS: int = Field(default_factory=lambda: int(os.getenv("MAX_POSITIONS", "1")))
    MAX_DAILY_LOSS_PERCENT: float = Field(default_factory=lambda: float(os.getenv("MAX_DAILY_LOSS_PERCENT", "5.0")))
    MAX_TRADES_PER_DAY: int = Field(default_factory=lambda: int(os.getenv("MAX_TRADES_PER_DAY", "10")))
    MAX_CONSECUTIVE_LOSSES: int = Field(default_factory=lambda: int(os.getenv("MAX_CONSECUTIVE_LOSSES", "3")))

    # Default Stops
    DEFAULT_SL_PIPS: float = Field(default_factory=lambda: float(os.getenv("DEFAULT_SL_PIPS", "50.0")))
    DEFAULT_TP_PIPS: float = Field(default_factory=lambda: float(os.getenv("DEFAULT_TP_PIPS", "150.0")))

    # Strategy Parameters matching Pine Script defaults
    EMA_LEN: int = Field(default=132)
    EMA_SRC: str = Field(default="close")
    EMA_SMOOTH_TYPE: str = Field(default="None")
    EMA_SMOOTH_LEN: int = Field(default=14)
    EMA_BB_MULT: float = Field(default=2.0)

    TAP_SOURCE: str = Field(default_factory=lambda: os.getenv("TAP_SOURCE", "TapByWick"))
    ZONE_BODY_PCT: float = Field(default_factory=lambda: float(os.getenv("ZONE_BODY_PCT", "1.0")))
    STOP_ON_TAP: bool = Field(default_factory=lambda: os.getenv("STOP_ON_TAP", "true").lower() == "true")
    ENABLE_ISS: bool = Field(default_factory=lambda: os.getenv("ENABLE_ISS", "true").lower() == "true")
    STOP_ISS_34_BY_WICK_TAP: bool = Field(default_factory=lambda: os.getenv("STOP_ISS_34_BY_WICK_TAP", "true").lower() == "true")

    # SMC Parameters
    SHOW_FVG: bool = Field(default_factory=lambda: os.getenv("SHOW_FVG", "false").lower() == "true")
    FVG_DELETE_ON_TAP: bool = Field(default_factory=lambda: os.getenv("FVG_DELETE_ON_TAP", "true").lower() == "true")
    MAX_FVG: int = Field(default_factory=lambda: int(os.getenv("MAX_FVG", "30")))
    SHOW_OB: bool = Field(default_factory=lambda: os.getenv("SHOW_OB", "false").lower() == "true")
    OB_DELETE_ON_TAP: bool = Field(default_factory=lambda: os.getenv("OB_DELETE_ON_TAP", "true").lower() == "true")
    MAX_OB: int = Field(default_factory=lambda: int(os.getenv("MAX_OB", "20")))
    SHOW_KZ: bool = Field(default_factory=lambda: os.getenv("SHOW_KZ", "false").lower() == "true")

    # Display / Limits
    MAX_LIVE_LEVELS: int = Field(default=140)

    # Level Analyzer
    SHOW_LEVEL_ANALYZER: bool = Field(default_factory=lambda: os.getenv("SHOW_LEVEL_ANALYZER", "false").lower() == "true")
    ANALYZER_TARGET_PIPS: float = Field(default_factory=lambda: float(os.getenv("ANALYZER_TARGET_PIPS", "150.0")))
    ANALYZER_LOSS_PIPS: float = Field(default_factory=lambda: float(os.getenv("ANALYZER_LOSS_PIPS", "50.0")))
    ANALYZER_MIN_DONE: int = Field(default_factory=lambda: int(os.getenv("ANALYZER_MIN_DONE", "3")))

    # System Parameters
    DEBUG: bool = Field(default_factory=lambda: os.getenv("DEBUG", "true").lower() == "true")
    LOG_LEVEL: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    POLL_INTERVAL_SECONDS: float = Field(default_factory=lambda: float(os.getenv("POLL_INTERVAL_SECONDS", "1.0")))

config = Config()
