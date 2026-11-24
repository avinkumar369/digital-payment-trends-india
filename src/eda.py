"""Exploratory Data Analysis for "Digital Payment Trends in India: UPI and Beyond".

Works on the four tables produced by ``src/preprocessing.py``:

  series          monthly UPI figures          (upi_merged.csv)
  instruments     instrument x period          (rbi_instruments.csv)
  infrastructure  acceptance infrastructure    (rbi_infrastructure.csv)
  fraud           monthly domestic frauds      (fraud_monthly.csv)

Run it to print the whole analysis, or import the individual functions:

    python -m src.eda

Every function returns a DataFrame or a plain dict, so the numbers can be reused
in the report and the deck without being retyped.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

RETAIL_CODES = ["2.6", "2.5", "2.3", "4.1", "4.2", "5.1", "5.2", "6.1", "2.2", "2.4", "3.2"]
LABELS = {
    "2.6": "UPI", "2.5": "NEFT", "2.3": "IMPS", "4.1": "Credit Card", "4.2": "Debit Card",
    "5.1": "Wallets", "5.2": "PPI Cards", "6.1": "CTS", "2.2": "APBS", "2.4": "NACH (Cr)",
    "3.2": "NACH (Dr)", "1": "RTGS", "3.1": "BHIM Aadhaar", "3.3": "NETC", "2.1": "AePS",
}


# --------------------------------------------------------------------------- #
# Generic statistics (the three functions the project already had)
# --------------------------------------------------------------------------- #
def descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Count, mean, std, min, quartiles and max for the numeric columns."""
    numeric = df.select_dtypes(include=[np.number])
    return numeric.describe().transpose()


def monthly_growth(df: pd.DataFrame, column: str) -> pd.Series:
    """Month-on-month percentage growth of one column, indexed by month."""
    growth = df.set_index("month")[column].pct_change() * 100
    growth.name = f"{column}_mom_growth"
    return growth


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation matrix for the numeric columns."""
    numeric = df.select_dtypes(include=[np.number])
    return numeric.corr()


# --------------------------------------------------------------------------- #
# Instrument mix
# --------------------------------------------------------------------------- #
def _slice(instruments: pd.DataFrame, period: str, codes: list[str] | None = None) -> pd.DataFrame:
    codes = codes or RETAIL_CODES
    sub = instruments[(instruments["period"] == period) & (instruments["code"].isin(codes))].copy()
    sub["label"] = sub["code"].map(LABELS).fillna(sub["instrument"])
    return sub


def retail_total(instruments: pd.DataFrame, period: str) -> tuple[float, float]:
    """Total retail volume (Mn) and value (Rs Cr) for a period."""
    row = instruments[(instruments["is_total"]) & (instruments["period"] == period) &
                      (instruments["instrument"].str.startswith("Total Retail"))]
    if row.empty:
        return float("nan"), float("nan")
    return float(row["volume_mn"].iloc[0]), float(row["value_cr"].iloc[0])


def instrument_summary(instruments: pd.DataFrame, period: str) -> pd.DataFrame:
    """Volume, value, ticket size and share of retail for every instrument."""
    sub = _slice(instruments, period)
    total_vol, total_val = retail_total(instruments, period)
    sub = sub.assign(
        volume_share_pct=sub["volume_mn"] / total_vol * 100,
        value_share_pct=sub["value_cr"] / total_val * 100,
    )
    cols = ["label", "volume_mn", "value_cr", "avg_ticket_size",
            "volume_share_pct", "value_share_pct"]
    return sub[cols].sort_values("volume_mn", ascending=False).reset_index(drop=True)


def yoy_table(instruments: pd.DataFrame, period: str) -> pd.DataFrame:
    """Year-on-year change in volume, value and ticket size, per instrument."""
    prior = (pd.Timestamp(period + "-01") - pd.DateOffset(years=1)).strftime("%Y-%m")
    now = _slice(instruments, period).set_index("code")
    before = _slice(instruments, prior).set_index("code")
    rows = []
    for code in RETAIL_CODES:
        if code not in now.index or code not in before.index:
            continue
        rows.append({
            "instrument": LABELS.get(code, code),
            "volume_mn_now": now.loc[code, "volume_mn"],
            "volume_mn_before": before.loc[code, "volume_mn"],
            "volume_yoy_pct": (now.loc[code, "volume_mn"] / before.loc[code, "volume_mn"] - 1) * 100
            if before.loc[code, "volume_mn"] else np.nan,
            "value_cr_now": now.loc[code, "value_cr"],
            "value_yoy_pct": (now.loc[code, "value_cr"] / before.loc[code, "value_cr"] - 1) * 100
            if before.loc[code, "value_cr"] else np.nan,
            "ticket_now": now.loc[code, "avg_ticket_size"],
            "ticket_yoy_pct": (now.loc[code, "avg_ticket_size"] / before.loc[code, "avg_ticket_size"] - 1) * 100
            if before.loc[code, "avg_ticket_size"] else np.nan,
        })
    out = pd.DataFrame(rows)
    return out.sort_values("volume_yoy_pct", ascending=False).reset_index(drop=True)


def concentration(instruments: pd.DataFrame, period: str) -> dict:
    """How concentrated retail volume is: top-1 share and Herfindahl index."""
    sub = _slice(instruments, period)
    total_vol, _ = retail_total(instruments, period)
    shares = (sub["volume_mn"] / total_vol).dropna()
    return {
        "top1_share_pct": float(shares.max() * 100),
        "top1_name": str(sub.loc[shares.idxmax(), "label"]) if len(shares) else "",
        "top3_share_pct": float(shares.nlargest(3).sum() * 100),
        "hhi": float((shares ** 2).sum() * 10000),
        "instrument_count": int(len(sub)),
    }


# --------------------------------------------------------------------------- #
# Time-series views
# --------------------------------------------------------------------------- #
def seasonality(series: pd.DataFrame) -> pd.DataFrame:
    """Average volume by calendar month, and an index against the overall mean."""
    tmp = series.assign(month_no=series["month"].dt.month,
                        month_name=series["month"].dt.strftime("%b"))
    grid = (tmp.groupby(["month_no", "month_name"])["upi_volume"]
            .agg(["mean", "count"]).reset_index())
    grid["index_vs_mean"] = grid["mean"] / series["upi_volume"].mean() * 100
    return grid.rename(columns={"mean": "avg_volume_mn", "count": "months_observed"})


def growth_summary(series: pd.DataFrame) -> dict:
    """Headline growth numbers for the UPI series."""
    first, last = series.iloc[0], series.iloc[-1]
    months = len(series)
    vol_cagr = ((last["upi_volume"] / first["upi_volume"]) ** (12 / max(months - 1, 1)) - 1) * 100
    return {
        "months": months,
        "from": first["month"].strftime("%b %Y"),
        "to": last["month"].strftime("%b %Y"),
        "volume_start_mn": float(first["upi_volume"]),
        "volume_end_mn": float(last["upi_volume"]),
        "volume_change_pct": float((last["upi_volume"] / first["upi_volume"] - 1) * 100),
        "value_change_pct": float((last["upi_value"] / first["upi_value"] - 1) * 100),
        "annualised_volume_pct": float(vol_cagr),
        "ticket_start_rs": float(first["upi_avg_ticket_size"]),
        "ticket_end_rs": float(last["upi_avg_ticket_size"]),
        "peak_month": series.loc[series["upi_volume"].idxmax(), "month"].strftime("%b %Y"),
        "peak_volume_mn": float(series["upi_volume"].max()),
        "trough_month": series.loc[series["upi_volume"].idxmin(), "month"].strftime("%b %Y"),
        "mean_mom_pct": float(series["upi_volume_mom_pct"].mean()),
    }


# --------------------------------------------------------------------------- #
# Fraud and infrastructure
# --------------------------------------------------------------------------- #
def fraud_summary(fraud: pd.DataFrame) -> dict:
    """Latest fraud reading, the 12-month average and the change since the start."""
    d = fraud.sort_values("month")
    last = d.iloc[-1]
    first = d.iloc[0]
    recent = d.tail(12)
    return {
        "months": len(d),
        "from": first["month"].strftime("%b %Y"),
        "to": last["month"].strftime("%b %Y"),
        "fraud_value_latest_cr": float(last["fraud_value_cr"]),
        "fraud_volume_latest_lakh": float(last["fraud_volume_lakh"]),
        "one_in_x_latest": float(last["one_in_x_transactions"]),
        "fts_latest_bps": float(last["fts_bps"]),
        "fts_mean_12m_bps": float(recent["fts_bps"].mean()),
        "fraud_value_mean_12m_cr": float(recent["fraud_value_cr"].mean()),
        "one_in_x_first": float(first["one_in_x_transactions"]),
        "fraud_value_change_pct": float((last["fraud_value_cr"] / first["fraud_value_cr"] - 1) * 100),
    }


def infrastructure_growth(infra: pd.DataFrame, start: str | None = None,
                          end: str | None = None) -> pd.DataFrame:
    """Change in every infrastructure metric between two periods (chronological).

    ``start`` and ``end`` are period keys such as '2025-09'. By default the
    earliest and the latest period in the table are used.
    """
    pivot = infra.pivot_table(index="metric", columns="period", values="value_lakh")
    cols = sorted(c for c in pivot.columns if not str(c).startswith("FY"))
    if len(cols) < 2:
        return pd.DataFrame()
    start = start or cols[0]
    end = end or cols[-1]
    if start not in pivot.columns or end not in pivot.columns:
        raise KeyError(f"periods {start!r}/{end!r} not in {list(pivot.columns)}")
    out = pd.DataFrame({
        "metric": pivot.index,
        start: pivot[start].values,
        end: pivot[end].values,
        "change_pct": (pivot[end] / pivot[start] - 1).mul(100).values,
    })
    return out.sort_values("change_pct", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def load_all() -> dict[str, pd.DataFrame]:
    tables = {
        "series": "upi_merged.csv",
        "instruments": "rbi_instruments.csv",
        "infrastructure": "rbi_infrastructure.csv",
        "fraud": "fraud_monthly.csv",
    }
    out = {}
    for name, filename in tables.items():
        path = PROCESSED / filename
        if path.exists():
            df = pd.read_csv(path)
            if "month" in df.columns:
                df["month"] = pd.to_datetime(df["month"], errors="coerce")
            out[name] = df
    return out


def main() -> None:
    data = load_all()
    if "series" not in data:
        raise SystemExit("Run `python -m src.preprocessing` first.")

    series = data["series"]
    print("=" * 78)
    print("1. DESCRIPTIVE STATISTICS - monthly UPI series")
    print(descriptive_stats(series[["upi_volume", "upi_value", "upi_avg_ticket_size",
                                    "upi_avg_daily_volume"]]).round(2).to_string())

    print("\n" + "=" * 78)
    print("2. GROWTH")
    for key, value in growth_summary(series).items():
        print(f"   {key:>26}: {value:,.2f}" if isinstance(value, float) else f"   {key:>26}: {value}")

    print("\n" + "=" * 78)
    print("3. CORRELATION - volume, value, ticket size")
    print(correlation_matrix(series[["upi_volume", "upi_value", "upi_avg_ticket_size"]])
          .round(3).to_string())

    print("\n" + "=" * 78)
    print("4. SEASONALITY (only months observed in the series)")
    print(seasonality(series).round(1).to_string(index=False))

    if "instruments" in data:
        inst = data["instruments"]
        period = sorted(p for p in inst["period"].unique() if not str(p).startswith("FY"))[-1]
        print("\n" + "=" * 78)
        print(f"5. INSTRUMENT MIX - {period}")
        print(instrument_summary(inst, period).round(2).to_string(index=False))

        print("\n" + "=" * 78)
        print("6. CONCENTRATION OF RETAIL VOLUME")
        for key, value in concentration(inst, period).items():
            print(f"   {key:>20}: {value}")

        print("\n" + "=" * 78)
        print("7. YEAR ON YEAR")
        print(yoy_table(inst, period).round(1).to_string(index=False))

    if "fraud" in data:
        print("\n" + "=" * 78)
        print("8. FRAUD")
        for key, value in fraud_summary(data["fraud"]).items():
            print(f"   {key:>26}: {value:,.2f}" if isinstance(value, float) else f"   {key:>26}: {value}")

    if "infrastructure" in data:
        print("\n" + "=" * 78)
        print("9. INFRASTRUCTURE GROWTH")
        print(infrastructure_growth(data["infrastructure"]).round(2).to_string(index=False))
    print("=" * 78)


if __name__ == "__main__":
    main()
