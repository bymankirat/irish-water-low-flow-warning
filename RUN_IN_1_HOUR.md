# Finish this project in 1 hour

Follow these steps in order. Times are approximate.

---

## Step 1: Set up (5 min)

1. Unzip this folder somewhere easy, e.g. `Documents/irish-water-low-flow-warning`.
2. Open a terminal in that folder and run:

```bash
pip install -r requirements.txt
python run_pipeline.py --demo
```

3. Open `docs/index.html` in your browser. You should see a report marked **DEMO DATA**.
   This proves everything works on your laptop. Demo numbers are fake: never publish them.

> Needs Python 3.10 or newer. If `python` doesn't work, try `python3`.

---

## Step 2: Get the real data (10 min)

```bash
python get_data.py
```

**Rainfall** downloads automatically (Cork Airport, Met Éireann). If it fails:
go to met.ie > Climate > Available Data > Historical Data, pick **Cork Airport**, download
**daily** data, and save it in `data/raw/` as `rain_3904.csv`.

**River flow** (by hand, 2 minutes):
1. Open https://waterlevel.ie/hydro-data/
2. Search for station **18055 Mallow Railway Br** (River Blackwater).
3. Pick the **discharge / flow (Q)** data, daily means if offered, the longest period, and download CSV or Excel.
4. Save it in `data/raw/` with a name starting with `flow`, e.g. `flow_18055.csv`.

15-minute data is fine; the code averages it to daily values.
If 18055 has no flow data (check with `wc -l`), pick another Cork river with "Water Level and Flow",
then change `FLOW_STATION` in `src/config.py` (number, name, river and published Q95).

---

## Step 3: Run it on the real data (5 min)

```bash
python run_pipeline.py
```

It prints a results table and creates:

- `docs/index.html`: your finished web report
- `reports/figures/`: 5 charts
- `reports/summary.md`: results table for your README and a **CV line with your real numbers**

**Before you publish, check:**
- The report has **no** orange DEMO banner.
- The dates at the bottom cover the years you expected.
- Your Q95 is in the same range as the EPA's published value shown in section 1.
  A big difference usually means the wrong file or units.

If the results are weak (for example 0 episodes warned early), that is still a real finding.
Say so honestly in the report and interview. Do **not** change the test years to make it look better.

---

## Step 4: Put it on GitHub with a live web page (15 min)

1. On github.com, create a new **public** repository called `irish-water-low-flow-warning`.
2. Upload the whole folder (drag and drop works), including `docs/` and `reports/`.
   Leave out `data/demo/` and `data/processed/`.
3. In the repository, open **Settings > Pages**. Under "Build and deployment" choose
   **Deploy from a branch**, branch **main**, folder **/docs**, then **Save**.
4. After 1 to 2 minutes your report is live at
   `https://bymankirat.github.io/irish-water-low-flow-warning/`
5. Open `README.md` on GitHub, click edit, and paste the table from `reports/summary.md`
   under **Results**.

---

## Step 5: Add it to your website and CV (15 min)

**Website:** add a project card linking to the GitHub Pages report. Use
`reports/figures/04_test_timeline.png` as the image and this text:

> **Will the river run low next week?** A 7-day early warning for Irish river low flows,
> built from public OPW/EPA and Met Éireann data and tested on years the model never saw.

**CV:** copy the CV line from `reports/summary.md` into the Data Projects section, at the top.
Add the report link.

**LinkedIn:** post 3 to 4 lines: what you built, one chart, the key result, and the link.

---

## Step 6: Prepare to talk about it (10 min)

Uisce Éireann's ad asks for problem solving, communication, initiative and curiosity.
Practise saying each of these out loud:

- **Why this project?** "I wanted to understand a real problem your operations teams deal
  with, so I built something using public Irish water data."
- **What was the problem?** Low river flows in late summer put pressure on water supply.
  A warning a week ahead gives time to act.
- **How did you make sure it was honest?** I split the data by time, tuned the alert level on
  separate years, and tested once on the most recent years the model never saw.
- **Why compare with a simple rule?** A model only matters if it beats what people already do.
  The rule can only react once the river is low; the model can warn before.
- **What would you do next?** Add rainfall forecasts, more rivers, and abstraction data, and
  talk to the operations team about what warning time they actually need.
- **Limits?** One river, few episodes in the test years, past rain only.

Know your 3 numbers by heart: episodes warned early, median head start, false alarms per year.
