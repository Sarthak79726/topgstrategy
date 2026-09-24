from typing import Optional, Dict, Any
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

from ..utils.logger import logger

class AccountManager:
    """Retrieves MT5 account details, balance, equity, margin, and trading permissions."""

    @staticmethod
    def get_account_info() -> Optional[Dict[str, Any]]:
        """Retrieve complete MT5 account info dictionary."""
        if not MT5_AVAILABLE:
            return None
        info = mt5.account_info()
        if info is None:
            logger.error("Failed to retrieve MT5 account info")
            return None

        return {
            "login": info.login,
            "trade_mode": info.trade_mode,
            "company": info.company,
            "currency": info.currency,
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.margin_free,
            "margin_level": info.margin_level,
            "leverage": info.leverage,
            "trade_allowed": info.trade_allowed,
            "trade_expert": info.trade_expert
        }

    @staticmethod
    def get_equity() -> float:
        """Get account equity (fallback to 10,000 if MT5 not available)."""
        if MT5_AVAILABLE:
            info = mt5.account_info()
            if info is not None:
                return info.equity
        return 10000.0

    @staticmethod
    def get_balance() -> float:
        """Get account balance (fallback to 10,000 if MT5 not available)."""
        if MT5_AVAILABLE:
            info = mt5.account_info()
            if info is not None:
                return info.balance
        return 10000.0
