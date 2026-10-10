"""Project settings. Change these if you pick a different river or weather station."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"
FIG_DIR = REPORTS_DIR / "figures"

# --- River flow station (OPW hydrometric network, waterlevel.ie) ---------------
# Default: River Blackwater at Mallow Railway Bridge, Co. Cork (station 18055).
# (Ballea, 19001, was the first choice, but its flow series is published with no values.)
# The EPA hydrometric register lists its published 95-percentile flow (Q95) as
# 3.667 m3/s, which we use as an independent check on our own calculation.
FLOW_STATION = {
    "number": "18055",
    "name": "Mallow Railway Bridge",
    "river": "Blackwater",
    "county": "Cork",
    "published_q95_m3s": 3.667,
}

# --- Rainfall station (Met Eireann daily data) ----------------------------------
# Cork Airport is about 35 km from Mallow; a closer gauge would be an improvement. Check the station number on
# met.ie > Climate > Available Data > Historical Data if the download fails.
RAIN_STATION = {"number": "3904", "name": "Cork Airport"}

# --- Analysis settings ------------------------------------------------------------
START_DATE = "2005-01-01"   # ignore older data (gauges and climate change over time)
FORECAST_DAYS = 7           # warn this many days ahead
TEST_YEARS = 3              # most recent years held back to test the model honestly
VALIDATION_YEARS = 2        # years before the test period, used to tune the alert level
RANDOM_STATE = 42
