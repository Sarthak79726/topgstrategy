import pandas as pd
from typing import Tuple

def validate_ohlcv_dataframe(df: pd.DataFrame) -> Tuple[bool, str]:
    """Validate that DataFrame has required OHLCV columns and is non-empty."""
    required_cols = {"open", "high", "low", "close"}
    if df is None or df.empty:
        return False, "DataFrame is empty or None"
    
    missing = required_cols - set(df.columns)
    if missing:
        return False, f"Missing required columns: {missing}"
    
    if len(df) < 2:
        return False, "DataFrame must contain at least 2 rows for bar calculations"
    
    return True, "Valid"
