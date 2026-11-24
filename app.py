"""Streamlit dashboard for "Digital Payment Trends in India: UPI and Beyond".

Four tables produced by ``src/preprocessing.py`` drive the page:

  data/processed/upi_merged.csv          monthly UPI series
  data/processed/rbi_instruments.csv     instrument x period volume and value
  data/processed/fraud_monthly.csv       monthly domestic payment frauds
  data/processed/rbi_infrastructure.csv  acceptance infrastructure

Run from the repository root:

    python -m src.preprocessing
    streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Digital Payment Trends in India - UPI and Beyond",
                   page_icon="", layout="wide")

ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"

SERIES_FILE = PROCESSED / "upi_merged.csv"
INSTRUMENTS_FILE = PROCESSED / "rbi_instruments.csv"
FRAUD_FILE = PROCESSED / "fraud_monthly.csv"
INFRA_FILE = PROCESSED / "rbi_infrastructure.csv"

REQUIRED_SERIES = ["month", "upi_volume", "upi_value",
                   "upi_avg_daily_volume", "upi_avg_daily_value"]

# Streamlit renamed this argument in 1.49; support both.
_ST_VER = tuple(int(p) for p in st.__version__.split(".")[:2] if p.isdigit())
CHART_KW = {"width": "stretch"} if _ST_VER >= (1, 49) else {"use_container_width": True}


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def load_csv(path: str, modified: float) -> pd.DataFrame:
    # ``modified`` is part of the cache key so a rebuilt CSV is picked up at once.
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    if "month" in df.columns:
        df["month"] = pd.to_datetime(df["month"], errors="coerce")
        df = df.dropna(subset=["month"]).sort_values("month").reset_index(drop=True)
    return df


def try_load(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        return load_csv(str(path), path.stat().st_mtime)
    except Exception as exc:  # noqa: BLE001 - show the reason, do not crash
        st.warning(f"Could not read `{path.name}`: {exc}")
        return None


series = try_load(SERIES_FILE)
instruments = try_load(INSTRUMENTS_FILE)
fraud = try_load(FRAUD_FILE)
infrastructure = try_load(INFRA_FILE)

if series is None and instruments is None:
    st.error(
        "No processed data found.\n\n"
        "Run the preprocessing step from the repository root:\n\n"
        "```bash\npython -m src.preprocessing\n```\n\n"
        f"Expected files in `{PROCESSED.relative_to(ROOT)}`."
    )
    st.stop()

if series is not None:
    missing = [c for c in REQUIRED_SERIES if c not in series.columns]
    if missing:
        st.error(
            f"`{SERIES_FILE.name}` is missing the column(s) the dashboard needs: {missing}.\n\n"
            f"Columns found: `{list(series.columns)}`\n\n"
            "Rebuild it with `python -m src.preprocessing`."
        )
        st.stop()

# --------------------------------------------------------------------------- #
# Header and filters
# --------------------------------------------------------------------------- #
st.title("Digital Payment Trends in India: UPI and Beyond")
st.caption(
    "Ten months of UPI statistics from NPCI, set against the RBI's payment-system "
    "indicators: how UPI compares with NEFT, IMPS, RTGS and cards, where acceptance "
    "is growing, and what fraud looks like at this scale."
)

with st.sidebar:
    st.header("Filters")
    if series is not None:
        min_date, max_date = series["month"].min(), series["month"].max()
        picked = st.date_input("UPI series - date range", value=(min_date, max_date),
                               min_value=min_date, max_value=max_date)
        if isinstance(picked, (tuple, list)) and len(picked) == 2:
            mask = (series["month"] >= pd.Timestamp(picked[0])) & (series["month"] <= pd.Timestamp(picked[1]))
            series_view = series.loc[mask].copy()
        else:
            series_view = series.copy()
        if series_view.empty:
            series_view = series.copy()
            st.caption("Empty range - showing all months.")
        st.caption(f"{len(series_view)} of {len(series)} months selected.")

    period = None
    if instruments is not None:
        options = instruments.dropna(subset=["period"]).drop_duplicates("period").copy()
        options["is_fy"] = options["period"].str.startswith("FY")
        # The fiscal-year-till-date column first, then the months oldest to newest.
        options = options.sort_values(["is_fy", "period"], ascending=[False, True])
        labels = list(options["period_label"])
        values = list(options["period"])
        default = len(values) - 1                       # latest month by default
        chosen = st.selectbox("Payment-mix snapshot", options=range(len(values)),
                              index=default, format_func=lambda i: labels[i])
        period = values[chosen]
    st.markdown("---")
    st.caption("Sources: NPCI UPI product statistics; RBI Payment System Indicators "
               "(September 2026 release).")

# --------------------------------------------------------------------------- #
# KPI strip - the UPI series
# --------------------------------------------------------------------------- #
if series is not None and not series_view.empty:
    total_volume = series_view["upi_volume"].sum()
    total_value = series_view["upi_value"].sum()
    avg_daily_volume = series_view["upi_avg_daily_volume"].mean()
    avg_daily_value = series_view["upi_avg_daily_value"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("UPI transactions", f"{total_volume:,.0f} Mn",
              help="Sum of monthly volume in the selected range, in millions.")
    c2.metric("UPI value", f"Rs {total_value:,.0f} Cr",
              help="Sum of monthly value in the selected range, in rupees crore.")
    c3.metric("Average per day", f"{avg_daily_volume:,.0f} Mn",
              help="Mean of the monthly average daily volume.")
    c4.metric("Average per day (value)", f"Rs {avg_daily_value:,.0f} Cr")

    latest = series_view.iloc[-1]
    first = series_view.iloc[0]
    growth = (latest["upi_volume"] / first["upi_volume"] - 1) * 100 if first["upi_volume"] else None

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Average ticket size", f"Rs {latest['upi_avg_ticket_size']:,.0f}",
              help="Latest month: value divided by transaction count.")
    if growth is not None:
        d2.metric("Volume change over range", f"{growth:+.1f}%",
                  help=f"{first['month']:%b %Y} to {latest['month']:%b %Y}.")
    d3.metric("Months in view", f"{len(series_view)}")
    d4.metric("Peak month", f"{series_view['upi_volume'].max():,.0f} Mn",
              help=str(series_view.loc[series_view['upi_volume'].idxmax(), 'month'].strftime('%b %Y')))

# --------------------------------------------------------------------------- #
# KPI strip - where UPI sits in the payment mix
# --------------------------------------------------------------------------- #
def _retail_totals(df: pd.DataFrame, period: str) -> tuple[float, float]:
    row = df[(df["is_total"]) & (df["period"] == period) &
             (df["instrument"].str.startswith("Total Retail"))]
    if row.empty:
        return float("nan"), float("nan")
    return float(row["volume_mn"].iloc[0]), float(row["value_cr"].iloc[0])


if instruments is not None and period is not None:
    upi_row = instruments[(instruments["code"] == "2.6") & (instruments["period"] == period)]
    total_vol, total_val = _retail_totals(instruments, period)
    if not upi_row.empty and pd.notna(total_vol):
        upi_vol = float(upi_row["volume_mn"].iloc[0])
        upi_val = float(upi_row["value_cr"].iloc[0])
        st.markdown("---")
        st.markdown(f"**Where UPI sits in the payment mix - {upi_row['period_label'].iloc[0]}**")
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Share of retail transactions", f"{upi_vol / total_vol * 100:.1f}%",
                  help="UPI volume as a share of total retail payment volume.")
        e2.metric("Share of retail value", f"{upi_val / total_val * 100:.1f}%",
                  help="UPI value as a share of total retail payment value.")
        prior = None
        if not str(period).startswith("FY"):
            prior = (pd.Timestamp(period + "-01") - pd.DateOffset(years=1)).strftime("%Y-%m")
        before = instruments[(instruments["code"] == "2.6") & (instruments["period"] == prior)] \
            if prior else instruments.iloc[0:0]
        if not before.empty:
            e3.metric("UPI volume, year on year",
                      f"{(upi_vol / float(before['volume_mn'].iloc[0]) - 1) * 100:+.1f}%")
            e4.metric("UPI value, year on year",
                      f"{(upi_val / float(before['value_cr'].iloc[0]) - 1) * 100:+.1f}%")

st.markdown("---")

# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
from src.visualizations import (  # noqa: E402 - imported after the data guards
    area_chart_total_volume,
    bar_chart_payment_methods,
    donut_chart_method_distribution,
    dual_axis_upi,
    fraud_trend_chart,
    growth_chart_instruments,
    heatmap_monthly_patterns,
    infrastructure_chart,
    line_chart_upi_volume,
    scatter_volume_vs_value,
)

if series is not None:
    st.subheader("1. UPI transaction volume over time")
    st.plotly_chart(line_chart_upi_volume(series_view), **CHART_KW)

    st.subheader("2. Volume and value move together")
    st.plotly_chart(dual_axis_upi(series_view), **CHART_KW)

if instruments is not None and period is not None:
    left, right = st.columns(2)
    with left:
        st.subheader("3. Volume by instrument")
        st.plotly_chart(bar_chart_payment_methods(instruments, period), **CHART_KW)
    with right:
        st.subheader("4. Share of retail transactions")
        st.plotly_chart(donut_chart_method_distribution(instruments, period), **CHART_KW)

    st.subheader("5. Small tickets, big tickets: volume against value")
    st.plotly_chart(scatter_volume_vs_value(instruments, period), **CHART_KW)

    st.subheader("6. Who is growing, who is shrinking")
    st.plotly_chart(growth_chart_instruments(instruments, period), **CHART_KW)

if fraud is not None:
    st.subheader("7. Fraud at this scale")
    st.plotly_chart(fraud_trend_chart(fraud), **CHART_KW)

if infrastructure is not None:
    st.subheader("8. Where acceptance is being built")
    st.plotly_chart(infrastructure_chart(infrastructure), **CHART_KW)

if series is not None:
    with st.expander("More views: cumulative volume and month pattern"):
        st.plotly_chart(area_chart_total_volume(series_view), **CHART_KW)
        st.plotly_chart(heatmap_monthly_patterns(series_view), **CHART_KW)

st.markdown("---")
st.caption(
    "Data: NPCI UPI product statistics (monthly, Jun 2025 - Mar 2026) and RBI Payment "
    "System Indicators, September 2026 release. Volume in millions, value in rupees "
    "crore. Daily averages divide by the actual number of days in each month."
)
