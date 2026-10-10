"""Load and clean the two raw data sources.

River flow files exported from waterlevel.ie (OPW) or EPA HydroNet come in a few
layouts: metadata lines starting with '#', ';' or ',' separators, 15-minute or
daily values, CSV or Excel. `load_flow` handles all of these so you can drop in
whatever file the website gives you.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd

from config import RAW_DIR, START_DATE

DATE_START = re.compile(r"^\s*\"?(\d{4}-\d{2}-\d{2}|\d{1,2}[-/.][A-Za-z0-9]{1,3}[-/.]\d{2,4})")


# --------------------------------------------------------------------------- helpers
def _find_file(prefix: str, folder: Path = RAW_DIR) -> Path:
    """Return the first data file in `folder` whose name starts with `prefix`."""
    matches = sorted(
        p for p in folder.glob(f"{prefix}*")
        if p.suffix.lower() in {".csv", ".txt", ".xlsx", ".xls"}
    )
    if not matches:
        raise FileNotFoundError(
            f"No file starting with '{prefix}' in {folder}. "
            "See RUN_IN_1_HOUR.md, step 2, for how to download it."
        )
    return matches[0]


def _read_text(path: Path) -> str:
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not read {path}")


def _to_number(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.replace(" ", "", regex=False)
    # decimal commas (e.g. "0,271") are common in ';'-separated exports
    if s.str.contains(r"^-?\d+,\d+$", regex=True).mean() > 0.5:
        s = s.str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def _parse_dates(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.strip('"')
    # keep local clock time: drop any timezone suffix (Z, +01:00) instead of converting,
    # so a 00:00 Irish-summer-time reading stays on its own day
    s = s.str.replace(r"(Z|[+-]\d{2}:?\d{2})$", "", regex=True)
    iso = pd.to_datetime(s, format="ISO8601", errors="coerce")
    if iso.notna().mean() > 0.9:
        return iso
    return pd.to_datetime(s, dayfirst=True, errors="coerce")


# --------------------------------------------------------------------------- flow
def _check_is_discharge(path: Path, header_text: str) -> None:
    """Stop early if the file is water level (stage, metres) rather than flow (m3/s)."""
    head = header_text.lower()
    name = path.name.lower()
    says_flow = re.search(r"m3/s|m³/s|m\^3/s|cumec|discharge|parametertype_name;q\b", head)
    says_level = (
        re.search(r"stage|water ?level|parametertype_name;s\b|unitsymbol;m\s*$", head, re.M)
        or re.search(r"(^|[_\-\s])s[_\-\s]complete|_stage|water.?level", name)
    )
    if says_level and not says_flow:
        raise ValueError(
            f"{path.name} looks like WATER LEVEL (stage, in metres), not river FLOW. "
            "On waterlevel.ie/hydro-data use the 'Flow' column (Q, m3/s) "
            "and download that file instead."
        )


def load_flow(folder: Path = RAW_DIR) -> pd.Series:
    """Daily mean river flow (m3/s) as a Series indexed by date."""
    path = _find_file("flow", folder)

    # An Excel file renamed to .csv still starts with the zip signature "PK"
    is_excel = path.suffix.lower() in {".xlsx", ".xls"} or path.read_bytes()[:2] == b"PK"
    if is_excel:
        raw = pd.read_excel(path, header=None, dtype=str)
        text = "\n".join(";".join("" if pd.isna(v) else str(v) for v in row) for row in raw.values)
    else:
        text = _read_text(path)

    lines = text.splitlines()
    first_data = next((i for i, ln in enumerate(lines) if DATE_START.match(ln)), None)
    if first_data is None:
        raise ValueError(f"Could not find any dated rows in {path.name}")

    _check_is_discharge(path, "\n".join(lines[:first_data]))

    header_line = ""
    for ln in reversed(lines[:first_data]):
        if ln.strip():
            header_line = ln.lstrip("#").strip()
            break

    sample = lines[first_data]
    sep = max([";", "\t", ","], key=sample.count)
    body = "\n".join(ln for ln in lines[first_data:] if ln.strip() and not ln.startswith("#"))
    df = pd.read_csv(io.StringIO(body), sep=sep, header=None, dtype=str, engine="python")

    names = [c.strip().strip('"') for c in header_line.split(sep)] if header_line else []
    if len(names) == df.shape[1]:
        df.columns = names
    else:
        df.columns = [f"col{i}" for i in range(df.shape[1])]

    date_col = df.columns[0]
    value_col = next(
        (c for c in df.columns[1:] if re.search(r"mean|value|discharge|flow|^q$|m3|m³", str(c), re.I)),
        df.columns[1],
    )

    out = pd.DataFrame({"date": _parse_dates(df[date_col]), "flow": _to_number(df[value_col])})
    out = out.dropna().set_index("date").sort_index()
    out = out[out["flow"] >= 0]

    daily = out["flow"].resample("D").mean()
    daily.name = "flow_m3s"
    return daily[daily.index >= START_DATE]


# --------------------------------------------------------------------------- rain
def load_rain(folder: Path = RAW_DIR) -> pd.Series:
    """Daily rainfall (mm) from a Met Eireann daily data file."""
    path = _find_file("rain", folder)
    lines = _read_text(path).splitlines()

    header_idx = next(
        (i for i, ln in enumerate(lines) if ln.lower().replace('"', "").startswith("date,")), None
    )
    if header_idx is None:
        raise ValueError(
            f"{path.name} does not look like a Met Eireann daily file (no 'date,' header line)."
        )

    df = pd.read_csv(io.StringIO("\n".join(lines[header_idx:])), dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    if "rain" not in df.columns:
        raise ValueError(f"No 'rain' column in {path.name}; columns are {list(df.columns)}")

    dates = pd.to_datetime(df["date"].str.strip(), format="%d-%b-%Y", errors="coerce")
    if dates.isna().mean() > 0.5:
        dates = pd.to_datetime(df["date"].str.strip(), dayfirst=True, errors="coerce")

    rain = pd.Series(_to_number(df["rain"]).values, index=dates, name="rain_mm")
    rain = rain[rain.index.notna()].sort_index()
    rain = rain[~rain.index.duplicated()].asfreq("D")
    return rain[rain.index >= START_DATE]


# --------------------------------------------------------------------------- combine
def load_dataset(folder: Path = RAW_DIR) -> tuple[pd.DataFrame, dict]:
    """Join flow and rain on date, fill short gaps only, and report data quality."""
    flow = load_flow(folder)
    rain = load_rain(folder)

    df = pd.concat([flow, rain], axis=1).loc[
        max(flow.first_valid_index(), rain.first_valid_index()):
        min(flow.last_valid_index(), rain.last_valid_index())
    ]

    quality = {
        "start": df.index.min().date().isoformat(),
        "end": df.index.max().date().isoformat(),
        "days": int(len(df)),
        "flow_missing_days": int(df["flow_m3s"].isna().sum()),
        "rain_missing_days": int(df["rain_mm"].isna().sum()),
    }

    # Fill gaps of up to 3 days by interpolation; longer gaps stay missing and
    # those days are dropped later rather than invented.
    df["flow_m3s"] = df["flow_m3s"].interpolate(limit=3, limit_area="inside")
    df["rain_mm"] = df["rain_mm"].fillna(0.0) if df["rain_mm"].isna().mean() < 0.01 else df["rain_mm"]
    quality["flow_missing_after_fill"] = int(df["flow_m3s"].isna().sum())
    quality["flow_missing_pct"] = round(100 * quality["flow_missing_days"] / max(len(df), 1), 2)
    return df, quality


if __name__ == "__main__":
    data, q = load_dataset()
    print(data.describe())
    print(q)
