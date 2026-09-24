from datetime import datetime, timezone
import pandas as pd

TIMEFRAME_MAP = {
    "M1": "1",
    "1": "1",
    "M3": "3",
    "3": "3",
    "M5": "5",
    "5": "5",
    "M15": "15",
    "15": "15",
    "M30": "30",
    "30": "30",
    "M45": "45",
    "45": "45",
    "H1": "60",
    "60": "60",
    "H2": "120",
    "120": "120",
    "H3": "180",
    "180": "180",
    "H4": "240",
    "240": "240",
    "D1": "D",
    "D": "D",
    "1D": "D",
    "W1": "W",
    "W": "W",
    "1W": "W",
    "MN1": "M",
    "M": "M",
    "1M": "M"
}

def parse_timeframe(tf_str: str) -> str:
    """Normalize timeframe string to standard format."""
    tf_upper = str(tf_str).upper()
    return TIMEFRAME_MAP.get(tf_upper, tf_str)

def timestamp_to_datetime(ts: int) -> datetime:
    """Convert unix timestamp to timezone-aware UTC datetime."""
    return datetime.fromtimestamp(ts, tz=timezone.utc)

def format_timestamp(dt: pd.Timestamp) -> str:
    """Format pandas Timestamp or datetime as standard ISO string."""
    if isinstance(dt, (int, float)):
        dt = pd.to_datetime(dt, unit="s", utc=True)
    return pd.to_datetime(dt).strftime("%Y-%m-%d %H:%M:%S")
