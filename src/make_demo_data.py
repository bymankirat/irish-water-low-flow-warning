"""Create FAKE demo files so you can test the pipeline before downloading real data.

    python src/make_demo_data.py

The numbers are simulated. Never publish results made from demo data:
run_pipeline.py labels every output "DEMO DATA" when these files are used.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from config import RAW_DIR

DEMO_DIR = RAW_DIR.parent / "demo"


def simulate(seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2005-01-01", "2025-12-31", freq="D")
    doy = dates.dayofyear.values

    # Wetter winters, drier summers, plus some dry and wet years
    wet_prob = 0.58 + 0.12 * np.cos(2 * np.pi * (doy - 15) / 365)
    year_factor = pd.Series(rng.normal(1.0, 0.15, len(dates.year.unique())), index=dates.year.unique())
    wet_prob = np.clip(wet_prob * year_factor.reindex(dates.year).values, 0.2, 0.9)
    rain = np.where(rng.random(len(dates)) < wet_prob, rng.gamma(0.8, 4.5, len(dates)), 0.0)

    # Simple two-store catchment: fast runoff + slow groundwater, summer evaporation
    evap = 1.6 + 1.4 * np.sin(2 * np.pi * (doy - 100) / 365)
    soil, gw, flow = 60.0, 80.0, []
    for r, e in zip(rain, evap):
        soil = max(soil + r - e, 0.0)
        excess = max(soil - 120.0, 0.0)
        soil -= excess
        recharge = 0.03 * soil
        soil -= recharge
        gw += recharge + 0.3 * excess
        q = 0.7 * excess + 0.018 * gw
        gw -= 0.018 * gw
        flow.append(q)
    area_factor = 103.28 / 86.4  # mm/day over 103 km2 -> m3/s
    flow = np.array(flow) * area_factor * rng.lognormal(0, 0.03, len(dates))
    return pd.DataFrame({"rain_mm": rain.round(1), "flow_m3s": flow.round(3)}, index=dates)


def write_files(df: pd.DataFrame) -> None:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)

    # Flow: WISKI/OPW-style export (metadata lines, ';' separator)
    flow_path = DEMO_DIR / "flow_DEMO.csv"
    with flow_path.open("w") as f:
        f.write("#station_no;19001\n#station_name;DEMO DATA - NOT REAL\n#ts_unitsymbol;m3/s\n")
        f.write("#Timestamp;Value;Quality Code\n")
        for d, v in df["flow_m3s"].items():
            if np.random.random() < 0.003:  # a few missing values, like real data
                continue
            f.write(f"{d.strftime('%Y-%m-%dT09:00:00.000+00:00')};{v};31\n")

    # Rain: Met Eireann-style daily file (notes at top, then 'date,ind,rain,...')
    rain_path = DEMO_DIR / "rain_DEMO.csv"
    with rain_path.open("w") as f:
        f.write("Station Name: DEMO DATA - NOT REAL\nStation Height: 0 M\n\n")
        f.write("date:  -  00 to 00 utc\nrain:  -  Precipitation Amount (mm)\n\n")
        f.write("date,ind,rain,ind,maxtp\n")
        for d, v in df["rain_mm"].items():
            f.write(f"{d.strftime('%d-%b-%Y').lower()},0,{v},0,12.0\n")

    print(f"Demo files written to {DEMO_DIR}")


if __name__ == "__main__":
    write_files(simulate())
