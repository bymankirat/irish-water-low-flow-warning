"""Build a single self-contained HTML page (images embedded) for your website or GitHub Pages."""

from __future__ import annotations

import base64
import html
from datetime import date
from pathlib import Path

from config import FLOW_STATION, FORECAST_DAYS, RAIN_STATION, TEST_YEARS

AUTHOR = "Mankirat Singh"
LINKS = {
    "GitHub": "https://github.com/bymankirat",
    "LinkedIn": "https://linkedin.com/in/mankirat-singh-694440177",
}


def _img(path: str, alt: str) -> str:
    data = base64.b64encode(Path(path).read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}" alt="{html.escape(alt)}">'


def _pct(x: float | None) -> str:
    return "–" if x is None else f"{100 * x:.0f}%"


def _lead(days: int | None) -> str:
    if days is None:
        return "no"
    return f"{days} day{'s' if days != 1 else ''} before"


def build(results: dict, quality: dict, figs: dict, extra: dict, demo: bool) -> str:
    m, r, c = results["model"], results["simple_rule"], results["combined"]
    s = FLOW_STATION
    station = f"{s['river']} River at {s['name']}, Co. {s['county']}"
    eps = results["episodes_total"]
    peak_month = max(extra["seasonality"], key=extra["seasonality"].get)
    best_window = max(extra["rain_memory"], key=extra["rain_memory"].get)
    q95, pub = results["q95_m3s"], s.get("published_q95_m3s")

    demo_banner = (
        '<div class="banner">DEMO DATA: these results come from simulated numbers, '
        "not the real river. Download the real data and re-run before publishing.</div>"
        if demo else ""
    )
    q95_check = ""
    if pub and not demo:
        diff = 100 * (q95 - pub) / pub
        q95_check = (
            f"<p>As a sanity check, the EPA's hydrometric register lists this station's "
            f"95-percentile flow as {pub:.3f} m³/s, against my {q95:.3f} m³/s "
            f"({diff:+.0f}%). Some difference is expected, as the two cover different years.</p>"
        )

    ep_rows = "".join(
        f"<tr><td>{e['start']}</td><td class=\"num\">{e['length_days']}</td>"
        f"<td class=\"num\">{_lead(er['notice_days'])}</td><td class=\"num\">{_lead(e['notice_days'])}</td></tr>"
        for e, er in zip(c["episodes"], r["episodes"])
    ) or '<tr><td colspan="4">No low-flow episodes in the test years.</td></tr>'

    links = " · ".join(f'<a href="{u}">{k}</a>' for k, u in LINKS.items())
    p = results["periods"]

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>River Low-Flow Warning</title>
<style>
:root {{
  --bg:#fcfcfb; --card:#ffffff; --ink:#0b0b0b; --ink-2:#52514e; --line:#e4e3df;
  --accent:#2a78d6; --warn-bg:#fff4e5; --warn-ink:#7a3d00;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg:#1a1a19; --card:#232322; --ink:#f0efec; --ink-2:#c3c2b7; --line:#3a3a38;
    --accent:#3987e5; --warn-bg:#3a2a12; --warn-ink:#ffd08a;
  }}
  :root:not([data-theme="light"]) img {{ background:#fcfcfb; }}
}}
:root[data-theme="dark"] {{
  --bg:#1a1a19; --card:#232322; --ink:#f0efec; --ink-2:#c3c2b7; --line:#3a3a38;
  --accent:#3987e5; --warn-bg:#3a2a12; --warn-ink:#ffd08a;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
main {{ max-width:880px; margin:0 auto; padding:40px 16px 64px; }}
h1 {{ font-size:clamp(1.6rem,4vw,2.3rem); line-height:1.2; margin:0 0 8px; }}
h2 {{ font-size:1.3rem; margin:48px 0 8px; }}
.byline,.muted {{ color:var(--ink-2); }}
a {{ color:var(--accent); }}
.banner {{ background:var(--warn-bg); color:var(--warn-ink); padding:12px 16px;
  border-radius:8px; font-weight:600; margin:16px 0; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin:24px 0; }}
.tile {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; }}
.tile b {{ display:block; font-size:2rem; line-height:1.1; }}
.tile span {{ color:var(--ink-2); font-size:.92rem; line-height:1.4; display:block; margin-top:4px; }}
img {{ width:100%; height:auto; border:1px solid var(--line); border-radius:8px; margin:12px 0; }}
.table-wrap {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; margin:12px 0; font-size:.95rem; }}
th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); }}
th {{ color:var(--ink-2); font-weight:600; }}
td.num,th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
footer {{ margin-top:56px; padding-top:16px; border-top:1px solid var(--line); color:var(--ink-2); font-size:.9rem; }}
</style>
</head>
<body>
<main>
{demo_banner}
<h1>Will the river run low next week? A {FORECAST_DAYS}-day early warning for the {html.escape(s['river'])} River</h1>
<p class="byline">{AUTHOR} · {date.today():%B %Y} · {links}</p>

<p>When rivers run low, water suppliers have less to draw on and less room for error.
I used {quality['days'] // 365} years of public Irish river-flow and rainfall data to build a model that
warns {FORECAST_DAYS} days before the {html.escape(station)} drops below its low-flow line,
and tested it honestly on the most recent {TEST_YEARS} years, which it had never seen.</p>

<div class="tiles">
  <div class="tile"><b>{c['episodes_warned_ahead']} of {eps}</b><span>low-flow episodes warned before they began (simple rule: {r['episodes_warned_ahead']})</span></div>
  <div class="tile"><b>{c['episodes_full_week']} of {eps}</b><span>episodes flagged a full {FORECAST_DAYS} days ahead (simple rule: {r['episodes_full_week']})</span></div>
  <div class="tile"><b>{_pct(c['recall'])}</b><span>of low-flow days flagged a week ahead (simple rule: {_pct(r['recall'])})</span></div>
  <div class="tile"><b>{c['false_alarm_days_per_year']:.0f}</b><span>false-alarm days per year (simple rule: {r['false_alarm_days_per_year']:.0f})</span></div>
</div>

<h2>1. How often does the river run low?</h2>
<p>I use the <b>Q95</b> as the low-flow line: the flow the river stays above 95% of the time,
a standard low-flow measure in Irish hydrology. It is {q95:.3f} m³/s here.</p>
{q95_check}
{_img(figs['history'], 'Daily river flow over time with low-flow days highlighted')}

<h2>2. When does it happen?</h2>
<p>Low flows are a late-summer problem, peaking in <b>{peak_month}</b>. That is when an early warning is most useful.</p>
{_img(figs['season'], 'Share of low-flow days by month')}

<h2>3. Why can we see it coming?</h2>
<p>The river responds to rain over weeks, not days. Rain over the last <b>{best_window} days</b>
relates most strongly to flow a week later, because groundwater keeps feeding the river long
after the rain stops. That delay is what makes a forecast possible.</p>
{_img(figs['memory'], 'Correlation between past rainfall and future flow')}

<h2>4. Does the warning work on unseen years?</h2>
<p>The model was trained on {p['train'][0][:4]}–{p['train'][1][:4]}, its alert level was set on
{p['validation'][0][:4]}–{p['validation'][1][:4]} (treating a missed low-flow day as twice as costly as a false alarm),
and it was then tested once on {p['test'][0][:4]}–{p['test'][1][:4]}.
I compare it with the simple rule an operator might use: <i>"warn when the river is already below the line."</i>
That rule does well once a dry spell is under way, because low flows last for weeks, but it can only react.
The real test is the start of each episode: does the warning come <b>before</b> the river drops?
In practice the two work together, so the <b>warning system</b> raises an alert when either the model
forecasts low flow or the river is already low.</p>
{_img(figs['timeline'], 'Test years: river flow and model risk over time')}
<div class="table-wrap"><table>
<thead><tr><th>Test years ({results['test_days']} days, {results['test_low_flow_days']} low-flow)</th>
<th class="num">Simple rule</th><th class="num">Model</th><th class="num">Warning system</th></tr></thead>
<tbody>
<tr><td>Episodes warned before they began</td><td class="num">{r['episodes_warned_ahead']} of {eps}</td><td class="num">{m['episodes_warned_ahead']} of {eps}</td><td class="num">{c['episodes_warned_ahead']} of {eps}</td></tr>
<tr><td>Episodes flagged a full {FORECAST_DAYS} days ahead</td><td class="num">{r['episodes_full_week']} of {eps}</td><td class="num">{m['episodes_full_week']} of {eps}</td><td class="num">{c['episodes_full_week']} of {eps}</td></tr>
<tr><td>Low-flow days flagged a week ahead (recall)</td><td class="num">{_pct(r['recall'])}</td><td class="num">{_pct(m['recall'])}</td><td class="num">{_pct(c['recall'])}</td></tr>
<tr><td>Alerts that were right (precision)</td><td class="num">{_pct(r['precision'])}</td><td class="num">{_pct(m['precision'])}</td><td class="num">{_pct(c['precision'])}</td></tr>
<tr><td>False-alarm days per year</td><td class="num">{r['false_alarm_days_per_year']:.0f}</td><td class="num">{m['false_alarm_days_per_year']:.0f}</td><td class="num">{c['false_alarm_days_per_year']:.0f}</td></tr>
</tbody></table></div>
<p class="muted">The model's risk score ranks days well: ROC AUC {'–' if results['roc_auc'] is None else f"{results['roc_auc']:.2f}"} (1.0 is perfect, 0.5 is guessing).</p>

<h3>Every low-flow episode in the test years</h3>
<div class="table-wrap"><table>
<thead><tr><th>Episode began</th><th class="num">Length (days)</th><th class="num">Simple rule warned</th><th class="num">Warning system warned</th></tr></thead>
<tbody>{ep_rows}</tbody></table></div>

<h2>5. What drives the warning?</h2>
<p>To check the model learned something sensible, I scrambled each input in turn and measured how much worse it got.</p>
{_img(figs['importance'], 'Which inputs matter most to the model')}

<h2>What this means for a water utility</h2>
<p>A warning a week ahead gives time to check storage, plan abstraction and prepare customer
messaging before supply comes under pressure. The same approach can run on any gauged river
with a nearby rain gauge, so it could be scaled across many supply catchments.</p>

<h2>Limits and next steps</h2>
<ul>
<li>One river and one rain gauge. Next: repeat across several supply catchments and compare.</li>
<li>Uses past rain only. Adding Met Éireann's rainfall <i>forecast</i> should extend the warning time.</li>
<li>Does not include abstraction volumes or groundwater levels, which would sharpen the forecast.</li>
<li>The alert level favours catching low flows over avoiding false alarms
(about {c['false_alarm_days_per_year']:.0f} false-alarm days a year). In practice it would be set with the operations team,
who know the cost of each.</li>
<li>The test covers {eps} episode{'s' if eps != 1 else ''}, so the results are indicative, not final.</li>
<li>Rainfall comes from {RAIN_STATION['name']}, not inside the catchment; a closer gauge should help.</li>
</ul>

<footer>
<p><b>Data:</b> river flow, station {s['number']}, from the OPW / EPA hydrometric network
(waterlevel.ie, EPA HydroNet), CC BY 4.0. Daily rainfall, {RAIN_STATION['name']} (station {RAIN_STATION['number']}),
from Met Éireann, CC BY 4.0. Data from {quality['start']} to {quality['end']};
{quality['flow_missing_pct']}% of flow days were missing; gaps of up to 3 days were filled, longer gaps excluded.</p>
<p><b>Method:</b> Python, pandas, scikit-learn (random forest), matplotlib. Time-based train / validation / test split,
so the model is never tested on years it learned from. Code: <a href="{LINKS['GitHub']}">GitHub</a>.</p>
</footer>
</main>
</body>
</html>
"""
