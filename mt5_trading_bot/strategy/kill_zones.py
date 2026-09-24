from datetime import datetime, timezone
import pandas as pd
from typing import Tuple

def is_in_kill_zone(dt: pd.Timestamp) -> Tuple[bool, bool]:
    """
    Check if datetime falls within London KZ (06:30-08:00 UTC) or NY KZ (12:30-14:30 UTC).
    Returns (is_london, is_ny).
    Direct reproduction of Pine Script UTC Kill Zone calculation.
    """
    if dt is None or pd.isna(dt):
        return False, False

    dt_utc = pd.to_datetime(dt, utc=True)
    utc_tot = dt_utc.hour * 60 + dt_utc.minute

    is_london = 390 <= utc_tot < 480
    is_ny = 750 <= utc_tot < 870

    return is_london, is_ny
