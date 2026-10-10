"""Step 2: run the whole analysis, from raw files to the finished website report.

    python run_pipeline.py          # real data from data/raw/
    python run_pipeline.py --demo   # simulated test data (outputs marked DEMO)

Outputs:
    reports/figures/*.png      charts for your README, CV portfolio and slides
    reports/results.json       every number in the report
    reports/test_timeline.csv  day-by-day forecasts for the test years
    docs/index.html            one self-contained web page (GitHub Pages ready)
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

import charts  # noqa: E402
import modelling  # noqa: E402
import report  # noqa: E402
from config import FLOW_STATION, FORECAST_DAYS, PROCESSED_DIR, RAW_DIR, REPORTS_DIR  # noqa: E402
from data_loading import load_dataset  # noqa: E402
from features import build_features  # noqa: E402


def summary_markdown(results: dict, demo: bool) -> str:
    """Results table for the README and a CV line, filled with the real numbers."""
    r, m, c = results["simple_rule"], results["model"], results["combined"]
    eps, q = results["episodes_total"], results["data_quality"]
    p = results["periods"]
    years = int(q["end"][:4]) - int(q["start"][:4]) + 1
    test_years = int(p["test"][1][:4]) - int(p["test"][0][:4]) + 1
    auc = "n/a" if results["roc_auc"] is None else f"{results['roc_auc']:.2f}"
    warn = "> DEMO DATA - do not publish these numbers.\n\n" if demo else ""
    return f"""{warn}## Results (test years {p['test'][0][:4]}-{p['test'][1][:4]}, never seen in training)

| | Simple rule | Model | Warning system |
|---|---:|---:|---:|
| Low-flow episodes warned before they began | {r['episodes_warned_ahead']} of {eps} | {m['episodes_warned_ahead']} of {eps} | {c['episodes_warned_ahead']} of {eps} |
| Episodes flagged a full {FORECAST_DAYS} days ahead | {r['episodes_full_week']} of {eps} | {m['episodes_full_week']} of {eps} | {c['episodes_full_week']} of {eps} |
| Low-flow days flagged a week ahead | {r['recall']:.0%} | {m['recall']:.0%} | {c['recall']:.0%} |
| Alerts that were right | {r['precision']:.0%} | {m['precision']:.0%} | {c['precision']:.0%} |
| False-alarm days per year | {r['false_alarm_days_per_year']:.0f} | {m['false_alarm_days_per_year']:.0f} | {c['false_alarm_days_per_year']:.0f} |

Low-flow line (Q95): {results['q95_m3s']:.3f} m3/s. Model ROC AUC: {auc}.

## CV line

**River low-flow early warning (Python, pandas, scikit-learn):** built a 7-day early-warning model
for Irish river low flows from {years} years of OPW/EPA flow and Met Eireann rainfall data; on
{test_years} unseen test years it warned of {c['episodes_warned_ahead']} of {eps} low-flow episodes before they began
({c['episodes_full_week']} with a full week's notice) vs {r['episodes_warned_ahead']} for a simple threshold rule; published as a web report.
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", action="store_true", help="use simulated demo data")
    args = ap.parse_args()

    folder = RAW_DIR.parent / "demo" if args.demo else RAW_DIR
    if args.demo and not any(folder.glob("flow*")):
        from make_demo_data import simulate, write_files
        write_files(simulate())

    print("1/5  Loading and cleaning data ...")
    try:
        df, quality = load_dataset(folder)
    except (FileNotFoundError, ValueError) as e:
        sys.exit(f"\n[!] {e}\n    Run 'python get_data.py' first, or 'python run_pipeline.py --demo' to test.")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_DIR / "daily_flow_rain.csv", index_label="date")
    print(f"     {quality['days']} days, {quality['start']} to {quality['end']}, "
          f"{quality['flow_missing_pct']}% flow days missing")

    print("2/5  Building features ...")
    feat = build_features(df)

    print("3/5  Training and testing the model ...")
    results, timeline = modelling.run(feat)
    q95 = results["q95_m3s"]

    pub = FLOW_STATION.get("published_q95_m3s")
    if pub and not args.demo and not (pub / 3 <= q95 <= pub * 3):
        print(f"\n[!] WARNING: your low-flow line is {q95:.3f}, but the EPA publishes "
              f"{pub:.3f} m3/s for this station.")
        print("    This usually means the file is WATER LEVEL, not FLOW, or the wrong station.")
        print("    Do not publish these results until this is fixed.\n")

    print("4/5  Drawing charts ...")
    station = f"{FLOW_STATION['river']} River at {FLOW_STATION['name']}"
    figs = {"history": charts.flow_history(df, q95, station)}
    figs["season"], seasonality = charts.seasonality(df, q95)
    figs["memory"], memory = charts.rain_memory(feat)
    figs["timeline"] = charts.test_timeline(timeline, q95, results["alert_level"])
    figs["importance"] = charts.importance(results["importance"])

    print("5/5  Writing the report ...")
    extra = {"seasonality": seasonality, "rain_memory": memory}
    results.update({"data_quality": quality, **extra, "demo_data": args.demo})
    (REPORTS_DIR / "results.json").write_text(json.dumps(results, indent=2, default=str))
    timeline.to_csv(REPORTS_DIR / "test_timeline.csv", index_label="date", float_format="%.4f")

    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "index.html").write_text(report.build(results, quality, figs, extra, args.demo), encoding="utf-8")

    r, m, c = results["simple_rule"], results["model"], results["combined"]
    eps = results["episodes_total"]
    print("\n================ RESULTS ================" + ("  (DEMO DATA - NOT REAL)" if args.demo else ""))
    print(f"Low-flow line (Q95): {q95:.3f} m3/s   |   test years: {eps} low-flow episodes")
    print(f"{'':32}{'Simple rule':>13}{'Model':>9}{'System':>9}")
    print(f"{'Episodes warned before start':32}{r['episodes_warned_ahead']:>13}{m['episodes_warned_ahead']:>9}{c['episodes_warned_ahead']:>9}")
    print(f"{'Flagged a full week ahead':32}{r['episodes_full_week']:>13}{m['episodes_full_week']:>9}{c['episodes_full_week']:>9}")
    print(f"{'Low-flow days flagged (recall)':32}{r['recall']:>13.0%}{m['recall']:>9.0%}{c['recall']:>9.0%}")
    print(f"{'Precision':32}{r['precision']:>13.0%}{m['precision']:>9.0%}{c['precision']:>9.0%}")
    print(f"{'False-alarm days per year':32}{r['false_alarm_days_per_year']:>13.1f}{m['false_alarm_days_per_year']:>9.1f}{c['false_alarm_days_per_year']:>9.1f}")
    (REPORTS_DIR / "summary.md").write_text(summary_markdown(results, args.demo), encoding="utf-8")
    print(f"\nOpen the report: {docs / 'index.html'}")
    print(f"Ready-to-paste CV line and README results: {REPORTS_DIR / 'summary.md'}")


if __name__ == "__main__":
    main()
