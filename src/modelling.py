"""Train and test a 7-day low-flow early-warning model, compared with a simple rule.

Question answered: "Will this river fall below its low-flow level (Q95) in 7 days?"
A water utility uses a warning like this to plan abstraction, check reservoir
storage and prepare customer messaging before supply comes under pressure.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from config import FORECAST_DAYS, RANDOM_STATE, TEST_YEARS, VALIDATION_YEARS
from features import FEATURES, low_flow_threshold


def split_by_time(feat: pd.DataFrame):
    """Train on the past, tune on the next years, test on the most recent years."""
    end = feat.index.max()
    test_start = end - pd.DateOffset(years=TEST_YEARS) + pd.Timedelta(days=1)
    val_start = test_start - pd.DateOffset(years=VALIDATION_YEARS)
    train = feat[feat.index < val_start]
    val = feat[(feat.index >= val_start) & (feat.index < test_start)]
    test = feat[feat.index >= test_start]
    return train, val, test


def _clean(part: pd.DataFrame, q95: float):
    part = part.dropna(subset=FEATURES + ["flow_future"])
    return part[FEATURES], (part["flow_future"] < q95).astype(int), part


def _scores(y_true, y_pred, days: int) -> dict:
    years = days / 365.25
    false_alarms = int(((y_pred == 1) & (y_true == 0)).sum())
    return {
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "false_alarm_days_per_year": round(false_alarms / years, 1),
        "alert_days_per_year": round(int(y_pred.sum()) / years, 1),
    }


def _episodes(below: pd.Series, min_len: int = 7, max_gap: int = 2 * FORECAST_DAYS) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Low-flow episodes: runs below Q95 lasting at least `min_len` days.

    Runs separated by a short recovery (<= max_gap days) count as ONE episode, so a
    brief dip just before a dry spell is not mistaken for an early warning.
    """
    runs, start, prev = [], None, None
    for day, is_low in below.items():
        if is_low and start is None:
            start = day
        if not is_low and start is not None:
            runs.append((start, prev))
            start = None
        prev = day
    if start is not None:
        runs.append((start, prev))

    merged: list[list[pd.Timestamp]] = []
    for s, e in runs:
        if merged and (s - merged[-1][1]).days - 1 <= max_gap:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged if (e - s).days + 1 >= min_len]


def warning_lead_times(alerts: pd.Series, flow: pd.Series, q95: float) -> list[dict]:
    """For each low-flow episode: was there an alert in the 7 days BEFORE it began?

    An alert issued on day d is a forecast for day d + FORECAST_DAYS. So for an
    episode starting on day s:
      - "notice_days" = days between the first alert in [s-7, s-1] and s (1 to 7),
        or None if no alert came before the river was already low;
      - "full_week" = the alert issued on s-7, the forecast for day s itself, fired.
    Episodes that start in the first week of the test period are skipped, because
    there is no earlier forecast to judge.
    """
    out = []
    first_day = alerts.index.min() + pd.Timedelta(days=FORECAST_DAYS)
    for s, e in _episodes(flow < q95):
        if s < first_day:
            continue
        window = alerts.loc[s - pd.Timedelta(days=FORECAST_DAYS): s - pd.Timedelta(days=1)]
        fired = window[window == 1]
        out.append({
            "start": s.date().isoformat(),
            "end": e.date().isoformat(),
            "length_days": int((e - s).days + 1),
            "notice_days": int((s - fired.index[0]).days) if len(fired) else None,
            "full_week": bool(alerts.get(s - pd.Timedelta(days=FORECAST_DAYS), 0) == 1),
        })
    return out


def run(feat: pd.DataFrame) -> dict:
    train, val, test = split_by_time(feat)
    q95 = low_flow_threshold(train["flow_today"].dropna())

    X_tr, y_tr, _ = _clean(train, q95)
    X_va, y_va, _ = _clean(val, q95)
    X_te, y_te, te = _clean(test, q95)

    model = RandomForestClassifier(
        n_estimators=400,
        min_samples_leaf=5,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    ).fit(X_tr, y_tr)

    # Alert level, chosen on the validation years only (never the test years):
    # maximise F2, which counts a missed low-flow day as twice as costly as a
    # false alarm, as an early-warning system should. The level is capped at 0.5
    # so that a few unusual validation years cannot make the model too cautious.
    p_va = model.predict_proba(X_va)[:, 1]
    alert_level = 0.5
    if y_va.sum() > 0:
        levels = np.round(np.arange(0.05, 0.96, 0.01), 2)
        f2 = [fbeta_score(y_va, (p_va >= t).astype(int), beta=2, zero_division=0) for t in levels]
        alert_level = float(min(levels[int(np.argmax(f2))], 0.5))

    p_te = model.predict_proba(X_te)[:, 1]
    alerts = {
        # Simple rule an operator might use: warn once the river is ALREADY below Q95
        "simple_rule": (X_te["flow_today"] < q95).astype(int).values,
        "model": (p_te >= alert_level).astype(int),
    }
    # How it would be deployed: alert if the model forecasts low flow OR the river is already low
    alerts["combined"] = np.maximum(alerts["model"], alerts["simple_rule"])

    days = len(y_te)
    results = {
        "q95_m3s": q95,
        "alert_level": alert_level,
        "periods": {
            "train": [str(train.index.min().date()), str(train.index.max().date())],
            "validation": [str(val.index.min().date()), str(val.index.max().date())],
            "test": [str(test.index.min().date()), str(test.index.max().date())],
        },
        "test_days": days,
        "test_low_flow_days": int(y_te.sum()),
        "roc_auc": float(roc_auc_score(y_te, p_te)) if 0 < y_te.sum() < days else None,
        "pr_auc": float(average_precision_score(y_te, p_te)) if y_te.sum() > 0 else None,
    }

    flow_test = test["flow_today"].dropna()
    for name, a in alerts.items():
        eps = warning_lead_times(pd.Series(a, index=te.index), flow_test, q95)
        notice = [e["notice_days"] for e in eps if e["notice_days"] is not None]
        results[name] = {
            **_scores(y_te.values, a, days),
            "episodes": eps,
            "episodes_warned_ahead": len(notice),
            "episodes_full_week": sum(e["full_week"] for e in eps),
            "median_notice_days": float(np.median(notice)) if notice else 0.0,
        }
    results["episodes_total"] = len(results["model"]["episodes"])

    if y_te.sum() > 0:
        imp = permutation_importance(
            model, X_te, y_te, scoring="average_precision",
            n_repeats=5, random_state=RANDOM_STATE, n_jobs=1,
        )
        results["importance"] = (
            pd.Series(imp.importances_mean, index=FEATURES).sort_values(ascending=False).to_dict()
        )
    else:
        results["importance"] = {}

    timeline = pd.DataFrame({
        "flow_m3s": te["flow_today"],
        "flow_in_7d_m3s": te["flow_future"],
        "low_flow_risk": p_te,
        "model_alert": alerts["model"],
        "rule_alert": alerts["simple_rule"],
        "combined_alert": alerts["combined"],
    })
    return results, timeline
