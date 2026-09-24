import pandas as pd
from typing import Optional
from .state import Snap

def init_snap() -> Snap:
    """Initialize empty Snap object."""
    return Snap(t=0, bar=0, o=0.0, c=0.0, h=0.0, l=0.0, lvl=0.0)

def make_snap_current(bar_index: int, open_: float, close_: float, high_: float, low_: float, level: float, time_ts: int = 0) -> Snap:
    """Create a Snap object for the current bar."""
    return Snap(t=time_ts, bar=bar_index, o=open_, c=close_, h=high_, l=low_, lvl=level)

def make_snap_at_bar(src_bar: int, level: float, df: pd.DataFrame, current_bar: int) -> Snap:
    """Create a Snap object for a historical bar by searching DataFrame bar_index."""
    off = current_bar - src_bar
    if off >= 0 and src_bar in df["bar_index"].values:
        row = df[df["bar_index"] == src_bar].iloc[0]
        ts = int(row["time"].timestamp()) if isinstance(row["time"], pd.Timestamp) else int(row["time"])
        return Snap(t=ts, bar=int(row["bar_index"]), o=float(row["open"]), c=float(row["close"]),
                    h=float(row["high"]), l=float(row["low"]), lvl=float(level))
    return init_snap()
