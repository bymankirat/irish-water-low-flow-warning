"""Turn daily flow and rain into model inputs.

Every feature uses only information available on the day the forecast is made,
so the model never 'sees the future'.
"""

import numpy as np
import pandas as pd

from config import FORECAST_DAYS

RAIN_WINDOWS = [1, 3, 7, 14, 30, 60, 90]


def low_flow_threshold(flow: pd.Series) -> float:
    """Q95: the flow exceeded 95% of the time, the standard Irish low-flow index."""
    return float(flow.quantile(0.05))


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    flow, rain = df["flow_m3s"], df["rain_mm"]

    out["flow_today"] = flow
    out["flow_mean_7d"] = flow.rolling(7, min_periods=5).mean()
    out["flow_min_30d"] = flow.rolling(30, min_periods=20).min()
    out["flow_change_7d_pct"] = 100 * (flow / flow.shift(7) - 1)

    for w in RAIN_WINDOWS:
        out[f"rain_{w}d_mm"] = rain.rolling(w, min_periods=max(1, int(0.8 * w))).sum()

    # how many days since a 'real' rain event (>= 5 mm)
    wet = (rain >= 5).astype(int)
    groups = wet.cumsum()
    out["days_since_5mm_rain"] = wet.groupby(groups).cumcount().where(groups > 0)

    doy = df.index.dayofyear
    out["season_sin"] = np.sin(2 * np.pi * doy / 365.25)
    out["season_cos"] = np.cos(2 * np.pi * doy / 365.25)

    # What we want to predict: the flow FORECAST_DAYS from now
    out["flow_future"] = flow.shift(-FORECAST_DAYS)
    return out


FEATURES = (
    ["flow_today", "flow_mean_7d", "flow_min_30d", "flow_change_7d_pct"]
    + [f"rain_{w}d_mm" for w in RAIN_WINDOWS]
    + ["days_since_5mm_rain", "season_sin", "season_cos"]
)

FEATURE_LABELS = {
    "flow_today": "River flow today",
    "flow_mean_7d": "Average flow, last 7 days",
    "flow_min_30d": "Lowest flow, last 30 days",
    "flow_change_7d_pct": "Flow change over 7 days (%)",
    "days_since_5mm_rain": "Days since 5 mm+ rain",
    "season_sin": "Time of year (sin)",
    "season_cos": "Time of year (cos)",
    **{f"rain_{w}d_mm": f"Rain, last {w} day{'s' if w > 1 else ''}" for w in RAIN_WINDOWS},
}
