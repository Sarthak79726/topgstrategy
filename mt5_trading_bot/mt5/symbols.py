import math
from typing import Optional, Dict, Any
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

from ..utils.logger import logger

class SymbolManager:
    """Handles symbol lookup, selection, pip size calculation and lot size normalization."""

    def __init__(self, target_symbol: str = "XAUUSD"):
        self.target_symbol = target_symbol
        self.resolved_symbol = target_symbol
        self.symbol_info: Optional[Any] = None

    def resolve_symbol(self) -> str:
        """Find matching broker symbol (e.g. XAUUSD, XAUUSDm, GOLD, XAUUSD.a)."""
        if not MT5_AVAILABLE:
            return self.target_symbol

        # Check exact symbol
        info = mt5.symbol_info(self.target_symbol)
        if info is not None:
            self.resolved_symbol = self.target_symbol
            self.symbol_info = info
            self.select_symbol(self.resolved_symbol)
            return self.resolved_symbol

        # Search for matching symbols in MT5
        all_symbols = mt5.symbols_get()
        if all_symbols:
            base_clean = self.target_symbol.upper().replace(".","").replace("-","").replace("_","")
            for sym in all_symbols:
                s_name = sym.name
                s_clean = s_name.upper().replace(".","").replace("-","").replace("_","")
                if base_clean in s_clean or s_clean in base_clean or ("GOLD" in base_clean and "XAU" in s_clean) or ("XAU" in base_clean and "GOLD" in s_clean):
                    logger.info(f"Resolved requested symbol '{self.target_symbol}' to broker symbol '{s_name}'")
                    self.resolved_symbol = s_name
                    self.symbol_info = sym
                    self.select_symbol(self.resolved_symbol)
                    return self.resolved_symbol

        logger.warning(f"Could not resolve symbol '{self.target_symbol}' in MT5. Falling back to default name.")
        return self.target_symbol

    def select_symbol(self, symbol_name: str) -> bool:
        """Ensure symbol is visible in MT5 Market Watch."""
        if not MT5_AVAILABLE:
            return True
        selected = mt5.symbol_select(symbol_name, True)
        if not selected:
            logger.error(f"Failed to select symbol '{symbol_name}' in MT5 Market Watch")
        return selected

    def get_pip_size(self, symbol_name: Optional[str] = None) -> float:
        """
        Calculate instrument-aware pip size.
        For Forex with 3 or 5 digits, 1 pip = 10 * point (e.g., 0.0001 for EURUSD, 0.01 for USDJPY).
        For Gold/XAUUSD or 2-digit pairs, 1 pip = 0.1 or 0.01 depending on digits.
        """
        sym = symbol_name or self.resolved_symbol
        if MT5_AVAILABLE:
            info = mt5.symbol_info(sym)
            if info is not None:
                point = info.point
                digits = info.digits
                if "XAU" in sym.upper() or "GOLD" in sym.upper():
                    return 0.1 if digits == 2 else 0.01 if digits == 3 else point * 10.0
                if digits in (3, 5):
                    return point * 10.0
                return point

        # Fallback heuristic
        sym_u = sym.upper()
        if "XAU" in sym_u or "GOLD" in sym_u:
            return 0.1
        elif "JPY" in sym_u:
            return 0.01
        return 0.0001

    def normalize_volume(self, volume: float, symbol_name: Optional[str] = None) -> float:
        """Normalize order volume/lot size according to broker constraints (vol_min, vol_max, vol_step)."""
        sym = symbol_name or self.resolved_symbol
        vol_min = 0.01
        vol_max = 100.0
        vol_step = 0.01

        if MT5_AVAILABLE:
            info = mt5.symbol_info(sym)
            if info is not None:
                vol_min = info.volume_min
                vol_max = info.volume_max
                vol_step = info.volume_step

        if volume < vol_min:
            volume = vol_min
        if volume > vol_max:
            volume = vol_max

        # Round down to nearest volume_step multiple
        steps = math.floor(volume / vol_step)
        norm_vol = steps * vol_step

        # Round to precision matching step decimal count
        step_str = str(vol_step)
        decimals = len(step_str.split('.')[1]) if '.' in step_str else 2
        return round(norm_vol, decimals)
