"""Charts for the report. Each title states the finding, not just the topic."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from config import FIG_DIR, FORECAST_DAYS  # noqa: E402
from features import FEATURE_LABELS, RAIN_WINDOWS  # noqa: E402

BLUE = "#2a78d6"      # river flow / the model
ORANGE = "#eb6834"    # low-flow days / the simple rule
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"
LABEL_BOX = {"facecolor": SURFACE, "edgecolor": "none", "pad": 1.5}

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "font.size": 10.5,
    "font.family": "DejaVu Sans",
    "legend.frameon": False,
})


def _save(fig, name: str) -> str:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def _subtitle(ax, text: str) -> None:
    ax.text(0, 1.02, text, transform=ax.transAxes, color=INK_2, fontsize=10, va="bottom")


def flow_history(df: pd.DataFrame, q95: float, station: str) -> str:
    flow = df["flow_m3s"]
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.plot(flow.index, flow, color=BLUE, lw=0.8, label="Daily mean flow")
    low = flow.where(flow < q95)
    ax.plot(low.index, low, color=ORANGE, lw=1.6, label="Below low-flow line")
    ax.axhline(q95, color=INK_2, lw=1.2, ls="--")
    ax.text(flow.index[0], q95 * 0.82, f"Low-flow line (Q95) = {q95:.3f} m³/s",
            color=INK_2, fontsize=9.5, va="top", bbox=LABEL_BOX)
    ax.set_yscale("log")
    ax.set_ylabel("Flow (m³/s, log scale)")
    ax.legend(loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2, fontsize=9.5)
    pct = 100 * (flow < q95).mean()
    ax.set_title(f"{station}: the river drops below its low-flow line on {pct:.0f}% of days", pad=26)
    _subtitle(ax, "Daily mean river flow, with low-flow days highlighted")
    return _save(fig, "01_flow_history.png")


def seasonality(df: pd.DataFrame, q95: float) -> tuple[str, dict]:
    by_month = (df["flow_m3s"] < q95).groupby(df.index.month).mean() * 100
    by_month = by_month.reindex(range(1, 13), fill_value=0)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    peak = by_month.idxmax()

    fig, ax = plt.subplots(figsize=(9, 3.8))
    bars = ax.bar(months, by_month.values, color=BLUE, width=0.7)
    for b, v in zip(bars, by_month.values):
        if v >= 1:
            ax.text(b.get_x() + b.get_width() / 2, v + 0.6, f"{v:.0f}%", ha="center",
                    color=INK_2, fontsize=9)
    ax.set_ylabel("Share of days below Q95 (%)")
    ax.grid(axis="x", visible=False)
    ax.set_title(f"Low flows cluster in late summer, peaking in {months[peak - 1]}", pad=26)
    _subtitle(ax, "Percentage of days in each month with flow below the low-flow line")
    return _save(fig, "02_seasonality.png"), {months[m - 1]: round(float(v), 1) for m, v in by_month.items()}


def rain_memory(feat: pd.DataFrame) -> tuple[str, dict]:
    d = feat.dropna(subset=["flow_future"])
    corr = {w: d[f"rain_{w}d_mm"].corr(d["flow_future"], method="spearman") for w in RAIN_WINDOWS}
    best = max(corr, key=corr.get)

    fig, ax = plt.subplots(figsize=(9, 3.8))
    labels = [f"{w} day{'s' if w > 1 else ''}" for w in RAIN_WINDOWS]
    colors = [BLUE if w == best else "#9fc3ee" for w in RAIN_WINDOWS]
    bars = ax.bar(labels, list(corr.values()), color=colors, width=0.7)
    for b, v in zip(bars, corr.values()):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.2f}", ha="center",
                color=INK_2, fontsize=9)
    ax.set_ylim(min(0, min(corr.values()) - 0.1), max(1.0, max(corr.values()) + 0.1))
    ax.set_xlabel("Rain added up over the last …")
    ax.set_ylabel("Rank correlation with\nflow in 7 days")
    ax.grid(axis="x", visible=False)
    ax.set_title(f"The river 'remembers' rain: the last {best} days matter most", pad=26)
    _subtitle(ax, f"How strongly past rainfall relates to river flow {FORECAST_DAYS} days later "
                  "(Spearman correlation)")
    return _save(fig, "03_rain_memory.png"), {str(k): round(float(v), 3) for k, v in corr.items()}


def test_timeline(tl: pd.DataFrame, q95: float, alert_level: float) -> str:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6.4), sharex=True,
                                   gridspec_kw={"height_ratios": [1.3, 1], "hspace": 0.12})
    ax1.plot(tl.index, tl["flow_m3s"], color=BLUE, lw=1)
    low = tl["flow_m3s"].where(tl["flow_m3s"] < q95)
    ax1.plot(low.index, low, color=ORANGE, lw=1.8)
    ax1.axhline(q95, color=INK_2, lw=1.1, ls="--")
    ax1.set_yscale("log")
    ax1.set_ylabel("Flow (m³/s, log)")
    ax1.text(tl.index[0], q95 * 0.8, "Low-flow line (Q95)", color=INK_2, fontsize=9, va="top", bbox=LABEL_BOX)
    ax1.set_title("On unseen recent years, the model's risk rises before the river runs low", pad=26)
    _subtitle(ax1, "Top: actual river flow (orange = below low-flow line).  "
                   f"Bottom: model's risk that flow will be low in {FORECAST_DAYS} days.")

    ax2.fill_between(tl.index, 0, tl["low_flow_risk"], color=BLUE, alpha=0.18, lw=0)
    ax2.plot(tl.index, tl["low_flow_risk"], color=BLUE, lw=1)
    ax2.axhline(alert_level, color=INK_2, lw=1.1, ls="--")
    ax2.text(tl.index[0], alert_level + 0.04, f"Alert level ({alert_level:.2f})", color=INK_2, fontsize=9, bbox=LABEL_BOX)
    ax2.set_ylim(0, 1.02)
    ax2.set_ylabel("Low-flow risk")
    return _save(fig, "04_test_timeline.png")


def importance(imp: dict) -> str:
    s = pd.Series(imp).sort_values().tail(8)
    s = s.clip(lower=0)
    fig, ax = plt.subplots(figsize=(8.5, 4))
    ax.barh([FEATURE_LABELS.get(k, k) for k in s.index], s.values, color=BLUE, height=0.6)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Drop in accuracy (average precision) when this input is scrambled")
    top = FEATURE_LABELS.get(s.index[-1], s.index[-1]).lower()
    ax.set_title(f"What drives the warning: {top} matters most", pad=26)
    _subtitle(ax, "Permutation importance on the test years (higher = more important)")
    return _save(fig, "05_what_drives_the_warning.png")

