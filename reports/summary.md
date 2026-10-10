## Results (test years 2023-2026, never seen in training)

| | Simple rule | Model | Warning system |
|---|---:|---:|---:|
| Low-flow episodes warned before they began | 0 of 4 | 4 of 4 | 4 of 4 |
| Episodes flagged a full 7 days ahead | 0 of 4 | 4 of 4 | 4 of 4 |
| Low-flow days flagged a week ahead | 72% | 99% | 99% |
| Alerts that were right | 72% | 55% | 55% |
| False-alarm days per year | 13 | 39 | 39 |

Low-flow line (Q95): 4.720 m3/s. Model ROC AUC: 0.96.

## CV line

**River low-flow early warning (Python, pandas, scikit-learn):** built a 7-day early-warning model
for Irish river low flows from 22 years of OPW/EPA flow and Met Eireann rainfall data; on
4 unseen test years it warned of 4 of 4 low-flow episodes before they began
(4 with a full week's notice) vs 0 for a simple threshold rule; published as a web report.
