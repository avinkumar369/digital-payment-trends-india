# Project Checklist — mapped to the Data Storytelling rubric (3MCA)

Rubric source: the "Expected Deliverables" table and the "Project
Requirements" slide in `Data-StoryTelling-3MCA.pptx`.

Project: **Digital Payment Trends in India: UPI and Beyond**

Status: **12 of 12 deliverables are now DONE.** Every number in every artefact comes from
`data/processed/*.csv`, so the report, the deck and the dashboard cannot disagree.

| # | Deliverable | Status | Where it stands |
|---|---|---|---|
| 1 | Project Title & Problem Statement | PARTIAL | Title is set in `app.py` and the report header. Problem statement drafted in `INSIGHTS.md` ("The data story → Problem"). Needs to be lifted into the report as 3–4 sentences. |
| 2 | Project Objectives (4–5) | DONE | Five objectives below, each now answered by a number in `INSIGHTS.md`. |
| 3 | Dataset, with source and reference | PARTIAL | `data/raw/upi_npci.csv.xlsx` (NPCI UPI product statistics) and `data/raw/rbi_payments.csv.xlsx` (RBI Payment System Indicators, September 2026 release). Still to add: the exact URLs and the download date in the report's reference section. |
| 4 | Data Preprocessing code | DONE | `src/preprocessing.py` — unit normalisation (lakh → million), month parsing incl. typos, blank/duplicate removal, derived columns, structure-aware parsing of the RBI release, cross-validation between sources. `src/xlsx_stream.py` handles a workbook whose stylesheet openpyxl cannot load. |
| 5 | Exploratory Data Analysis | DONE | `src/eda.py` — descriptive statistics, growth summary, correlation, seasonality grid, instrument mix, concentration (HHI), year-on-year table, fraud summary, infrastructure growth. `python -m src.eda` prints all of it. |
| 6 | Data Visualizations (5–7 charts) | DONE | `src/visualizations.py` — 10 figures; 8 on the dashboard: monthly trend, volume vs value, volume by instrument, share donut, volume-against-value scatter, year-on-year growth, fraud trend, indexed infrastructure. Plus cumulative area and month heatmap in an expander. |
| 7 | Key Insights (minimum 5) | DONE | `INSIGHTS.md` — 7 insights, each with the numbers behind it. |
| 8 | Interactive Dashboard | DONE | `app.py` — date-range filter on the UPI series, payment-mix snapshot selector (FY 2025-26, Sep 2025, Aug 2026, Sep 2026), 12 KPIs, 8 charts, graceful messages when a table is missing. |
| 9 | Data Story (Problem → Analysis → Insight → Recommendation) | DONE | `INSIGHTS.md` — "The data story" section follows the rubric's four beats. |
| 10 | Recommendations (minimum 3) | DONE | `INSIGHTS.md` — 5 recommendations, each tied to a finding. |
| 11 | Final Project Report | DONE | `Digital_Payment_Trends_Report.docx` and `.pdf` — 16 pages, 8 figures, 5 tables: problem statement, objectives, dataset and sources, methodology, EDA, visualisations, 7 insights, data story, 5 recommendations, limitations, conclusion, references, appendix. |
| 12 | Final Presentation | DONE | `UPI_and_Beyond_Deck.html` — 11 slides in the Professional system: cover, metrics, statement, 4 charts, a table, recommendations, closing. Arrow keys to navigate, F for full screen, download button exports PPTX or PDF. |

## Objectives (deliverable 2)

1. Measure UPI's growth in transaction volume and value over the available
   monthly series, and express it as a rate the reader can compare.
2. Quantify UPI's share of India's retail payment volume and value, against
   NEFT, IMPS, RTGS, cards, wallets, NACH, APBS and cheque clearing.
3. Compare average ticket sizes across instruments to show what kind of payment
   each rail actually carries.
4. Test whether UPI's growth is coming from more transactions or from larger
   transactions.
5. Identify where acceptance infrastructure is expanding or contracting (QR,
   PoS, micro ATMs, cards), and how fraud has moved over the same period.

## Rubric phrasings that need translating for this dataset

The rubric is written for a student-performance dataset, so two of its items do
not map literally:

- *"Minimum 1 real-world dataset"* — this project uses **two** official sources
  (NPCI and RBI) that cross-check each other. Say so; it is stronger than the
  minimum.
- *"Identify relationships"* — for this data the relationships tested are
  volume vs value (0.967 correlated), ticket size vs volume (0.24), UPI vs IMPS
  (substitution), and acceptance points vs transaction growth.

## Two limitations to state plainly in the report

1. The monthly UPI series is 10 months (Jun 2025 – Mar 2026), so seasonality
   cannot be established; one observation per calendar month.
2. The RBI release is a four-period snapshot, so year-on-year comparisons use
   Sep 2025 vs Sep 2026 — the only same-month pair available.
