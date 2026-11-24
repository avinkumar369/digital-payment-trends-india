# Digital Payment Trends in India: UPI and Beyond

How UPI scaled, where it sits against NEFT, IMPS, RTGS and cards, where
acceptance is being built, and what fraud looks like at this volume — built on
NPCI's monthly UPI statistics and the RBI's Payment System Indicators.

## Files

```
app.py                        Streamlit dashboard (entry point)
src/preprocessing.py          raw files  ->  four analysis-ready tables
src/visualizations.py         the Plotly figures used by the dashboard
src/eda.py                    exploratory analysis, printed as a report
src/xlsx_stream.py            stylesheet-free .xlsx reader (fallback)
INSIGHTS.md                   findings, data story and recommendations
PROJECT_CHECKLIST.md          the 12 rubric deliverables and their status
requirements.txt
```

## Run

```bash
pip install -r requirements.txt
python -m src.preprocessing     # builds data/processed/*.csv
python -m src.eda               # prints the analysis
streamlit run app.py            # http://localhost:8501
```

All three commands must run **from the repository root** so `data/raw/` and
`data/processed/` resolve.

## Inputs

| File | Contents |
|---|---|
| `data/raw/upi_npci.*` | NPCI UPI product statistics, one row per month |
| `data/raw/rbi_payments.*` | RBI Payment System Indicators release: PART I (payment and settlement statistics), PART III (infrastructure), PART V (domestic payment frauds) |

`.csv` and `.xlsx` are both accepted, and the file name only has to start with
`upi_npci` or `rbi_payments` (`upi_npci.csv.xlsx` works).

The parsers read the structure rather than fixed cell addresses: the PART
markers, the `Volume` / `Value` header block, the `1 2 3 4` numbering row and
the period labels above it are all located at run time, so a new monthly release
with the same layout drops straight in. Month names are parsed from `Jun-2025`,
`Jun-25`, `2025 June`, `June 2026` or `As on March 2026`, and month-name typos in
the source (`Jauuary 2025`) are repaired.

## Outputs

| File | One row per | Columns |
|---|---|---|
| `data/processed/upi_merged.csv` | month | `month`, `upi_volume` (Mn), `upi_value` (₹ Cr), `days_in_month`, `upi_avg_daily_volume`, `upi_avg_daily_value`, `upi_avg_ticket_size`, `upi_volume_mom_pct`, `upi_value_mom_pct` |
| `data/processed/rbi_instruments.csv` | instrument × period | `period`, `period_label`, `code`, `level`, `instrument`, `is_total`, `volume_mn`, `value_cr`, `avg_ticket_size` |
| `data/processed/rbi_infrastructure.csv` | metric × period | `period`, `period_label`, `metric`, `value_lakh` |
| `data/processed/fraud_monthly.csv` | month | `month`, `fraud_volume_lakh`, `fraud_value_cr`, `one_in_x_transactions`, `fts_bps` |

Units are normalised on the way in: RBI volume is reported in lakh and is
converted to millions (1 lakh = 0.1 Mn); all value stays in ₹ crore.

## Derived, not reported

The sources publish volume, value and their own daily averages. These are
computed here so the definition is explicit and consistent:

- `upi_avg_daily_volume` = volume ÷ actual days in that month (leap years handled)
- `upi_avg_ticket_size` = value × 10 ÷ volume, i.e. `(value_cr × 1e7) ÷ (volume_mn × 1e6)`, in ₹
- `*_mom_pct` = month-on-month change, blank on the first row and after any gap

The source's own `Avg. Daily Volume` columns are ignored rather than trusted, so
a month with missing data cannot silently carry a wrong daily average.

## Self-checks

Every run of `python -m src.preprocessing` prints:

- which files were found, how many months or metrics were kept, and how many
  rows were dropped as blank or duplicate;
- the periods found in the RBI release;
- a cross-check of UPI volume between the two sources for every overlapping
  month (NPCI and RBI must agree; for Sep 2025 both report 19,633.43 Mn).

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `No processed data found` | `data/processed/*.csv` absent | `python -m src.preprocessing` |
| `is missing the column(s) the dashboard needs` | an old processed file with different names | rerun preprocessing |
| `pandas/openpyxl could not read ...` (warning) | the RBI workbook's stylesheet is malformed | nothing to do — the built-in streaming reader takes over automatically |
| `No 'Volume'/'Value' header row` | the release layout changed | check that the PART headers still carry `Volume` and `Value`; the parsers locate rows by those words |
| Dashboard shows old numbers after a rebuild | Streamlit cache | the cache now keys on the file's modified time; press `R` if you still see stale figures |

## Data notes

- The RBI release states its data is provisional; the latest month can be revised.
- The monthly UPI series currently spans Jun 2025 – Mar 2026 (10 months). That is
  enough for trend and growth, not for seasonality — see INSIGHTS.md.
- Fraud-to-sales ratio (FTS) is quoted exactly as published. The published ratio
  and the published ₹ crore figures do not reconcile to one denominator, so FTS
  is used as a relative indicator and ₹ crore for levels.
