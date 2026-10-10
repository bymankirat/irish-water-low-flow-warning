"""Step 1: get the raw data into data/raw/.

Rainfall is downloaded automatically from Met Eireann.
River flow has to be downloaded by hand from waterlevel.ie (2 minutes); this
script prints exactly what to click.

    python get_data.py
"""

import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from config import FLOW_STATION, RAIN_STATION, RAW_DIR  # noqa: E402

RAIN_URL = "https://cli.fusio.net/cli/climate_data/webdata/dly{n}.csv"


def download_rain() -> bool:
    target = RAW_DIR / f"rain_{RAIN_STATION['number']}.csv"
    if target.exists():
        print(f"[ok] Rainfall already downloaded: {target.name}")
        return True
    url = RAIN_URL.format(n=RAIN_STATION["number"])
    print(f"Downloading daily rainfall for {RAIN_STATION['name']} ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        if b"date," not in data[:5000].lower():
            raise ValueError("unexpected file content")
        target.write_bytes(data)
        print(f"[ok] Saved {target.name} ({len(data) / 1e6:.1f} MB)")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[!] Automatic download failed ({e}). Do this instead:")
        print("    1. Go to met.ie > Climate > Available Data > Historical Data")
        print(f"    2. Pick '{RAIN_STATION['name']}', choose DAILY data, download the CSV")
        print(f"    3. Save it as {target}")
        return False


def explain_flow() -> bool:
    existing = [p for p in RAW_DIR.glob("flow*") if p.suffix.lower() in {".csv", ".txt", ".xlsx", ".xls"}]
    if existing:
        print(f"[ok] River flow file found: {existing[0].name}")
        return True
    s = FLOW_STATION
    print("\nRiver flow: download it by hand (about 2 minutes):")
    print("    1. Open https://waterlevel.ie/hydro-data/")
    print(f"    2. Search for station {s['number']} ({s['name']}, {s['river']} River)")
    print("    3. Choose the DISCHARGE (flow, 'Q') data, DAILY MEANS if offered,")
    print("       the longest period available, and download as CSV or Excel")
    print(f"    4. Save it in {RAW_DIR} with a name starting with 'flow', e.g. flow_{s['number']}.csv")
    print("    (15-minute data is fine too; the code converts it to daily averages.)")
    return False


if __name__ == "__main__":
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ok_rain = download_rain()
    ok_flow = explain_flow()
    if ok_rain and ok_flow:
        print("\nAll data in place. Next: python run_pipeline.py")
    else:
        print("\nWhen both files are in data/raw/, run: python run_pipeline.py")
