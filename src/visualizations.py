"""Plotly figures for the Digital Payment Trends dashboard.

Three tables feed these charts, all built by ``src/preprocessing.py``:

  * series        - monthly UPI figures (``upi_merged.csv``)
  * instruments   - tidy instrument x period volume/value (``rbi_instruments.csv``)
  * fraud         - monthly domestic payment frauds (``fraud_monthly.csv``)
  * infrastructure- acceptance infrastructure counts (``rbi_infrastructure.csv``)

Every function returns a ``plotly.graph_objects.Figure`` and never raises on an
empty selection: it returns an annotated blank figure instead, so the dashboard
stays usable at any filter setting.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ACCENT = "#1F6FEB"
ACCENT_2 = "#F2994A"
ACCENT_3 = "#27AE60"
MUTED = "#8A94A6"
NEGATIVE = "#EB5757"
SEQ = ["#1F6FEB", "#F2994A", "#27AE60", "#9B51E0", "#EB5757", "#2D9CDB", "#F2C94C",
       "#6FCF97", "#BB6BD9", "#56CCF2"]

LAYOUT = dict(
    template="plotly_white",
    margin=dict(l=60, r=30, t=60, b=50),
    font=dict(family="Inter, Segoe UI, sans-serif", size=13),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)

# Which rows of the RBI table are worth charting, by their section code.
RETAIL_CODES = ["2.6", "2.5", "2.3", "4.1", "4.2", "5.1", "5.2", "6.1", "2.2", "2.4", "3.2"]
INCLUDE_WHOLESALE = RETAIL_CODES + ["1"]

LABELS = {
    "2.6": "UPI", "2.5": "NEFT", "2.3": "IMPS", "4.1": "Credit Card", "4.2": "Debit Card",
    "5.1": "Wallets", "5.2": "PPI Cards", "6.1": "CTS", "2.2": "APBS", "2.4": "NACH (Cr)",
    "3.2": "NACH (Dr)", "1": "RTGS", "3.1": "BHIM Aadhaar", "3.3": "NETC", "2.1": "AePS",
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _empty(message: str, height: int = 380) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(**LAYOUT, height=height, xaxis=dict(visible=False),
                      yaxis=dict(visible=False))
    fig.add_annotation(text=message, showarrow=False, xref="paper", yref="paper",
                       x=0.5, y=0.5, font=dict(size=14, color=MUTED))
    return fig


def _prepare_series(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return pd.DataFrame()
    out = df.copy()
    out["month"] = pd.to_datetime(out["month"], errors="coerce")
    return out.dropna(subset=["month"]).sort_values("month").reset_index(drop=True)


def _months(df: pd.DataFrame) -> list[str]:
    """Month periods present in the instrument table, oldest first."""
    periods = [p for p in df["period"].dropna().unique() if not str(p).startswith("FY")]
    return sorted(periods)


def latest_period(df: pd.DataFrame) -> str | None:
    months = _months(df)
    return months[-1] if months else None


def _slice(df: pd.DataFrame, period: str, codes: list[str]) -> pd.DataFrame:
    """Rows for one period, restricted to the curated codes, in a stable order."""
    sub = df[(df["period"] == period) & (df["code"].isin(codes))].copy()
    # code '1' matches two rows: 'CCIL Operated Systems' and 'Credit Transfers -
    # RTGS'. Only RTGS is a payment instrument, so drop the CCIL row.
    if "instrument" in sub.columns:
        ccil = (sub["code"] == "1") & (~sub["instrument"].str.contains("RTGS", case=False, na=False))
        sub = sub[~ccil]
    sub["label"] = sub["code"].map(LABELS).fillna(sub["instrument"])
    sub["order"] = sub["code"].map({c: i for i, c in enumerate(codes)})
    return sub.sort_values("order").reset_index(drop=True)


def _year_ago(df: pd.DataFrame, period: str) -> str | None:
    """The same month one year earlier, if the table has it."""
    try:
        prior = (pd.Timestamp(period + "-01") - pd.DateOffset(years=1)).strftime("%Y-%m")
    except (ValueError, TypeError):
        return None
    return prior if prior in set(df["period"].unique()) else None


# --------------------------------------------------------------------------- #
# 1. Monthly trend
# --------------------------------------------------------------------------- #
def line_chart_upi_volume(df: pd.DataFrame) -> go.Figure:
    """UPI transactions per month, with a 3-month rolling average."""
    d = _prepare_series(df)
    if d.empty or "upi_volume" not in d.columns:
        return _empty("No UPI volume data in the selected range")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d["month"], y=d["upi_volume"], mode="lines+markers", name="Monthly volume",
        line=dict(color=ACCENT, width=3), marker=dict(size=7),
        hovertemplate="%{x|%b %Y}<br>%{y:,.0f} Mn transactions<extra></extra>",
    ))
    if len(d) >= 3:
        fig.add_trace(go.Scatter(
            x=d["month"], y=d["upi_volume"].rolling(3, min_periods=2).mean(),
            mode="lines", name="3-month average",
            line=dict(color=ACCENT_2, width=2, dash="dash"),
            hovertemplate="%{x|%b %Y}<br>%{y:,.0f} Mn<extra></extra>",
        ))
    fig.update_layout(**LAYOUT, height=420, title="UPI transactions per month (millions)",
                      yaxis_title="Volume (Mn)")
    return fig


# --------------------------------------------------------------------------- #
# 2. Volume and value together
# --------------------------------------------------------------------------- #
def dual_axis_upi(df: pd.DataFrame) -> go.Figure:
    """Volume as bars, value as a line on a second axis."""
    d = _prepare_series(df)
    if d.empty or "upi_volume" not in d.columns:
        return _empty("No UPI volume data in the selected range")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=d["month"], y=d["upi_volume"], name="Volume (Mn)",
                         marker_color="rgba(31,111,235,0.55)",
                         hovertemplate="%{x|%b %Y}<br>%{y:,.0f} Mn<extra></extra>"),
                  secondary_y=False)
    if "upi_value" in d.columns and d["upi_value"].notna().any():
        fig.add_trace(go.Scatter(x=d["month"], y=d["upi_value"], name="Value (Rs Cr)",
                                 mode="lines+markers", line=dict(color=ACCENT_2, width=3),
                                 marker=dict(size=6),
                                 hovertemplate="%{x|%b %Y}<br>Rs %{y:,.0f} Cr<extra></extra>"),
                      secondary_y=True)
    fig.update_layout(**LAYOUT, height=430, title="UPI volume (bars) and value (line)")
    fig.update_yaxes(title_text="Volume (Mn)", secondary_y=False)
    fig.update_yaxes(title_text="Value (Rs Cr)", secondary_y=True)
    return fig


# --------------------------------------------------------------------------- #
# 3. Instrument comparison, this month vs a year ago
# --------------------------------------------------------------------------- #
def bar_chart_payment_methods(df: pd.DataFrame, period: str | None = None) -> go.Figure:
    """Volume of each retail instrument, latest month against the same month a year earlier."""
    if df is None or len(df) == 0:
        return _empty("No instrument-level data available")
    period = period or latest_period(df)
    now = _slice(df, period, RETAIL_CODES)
    if now.empty:
        return _empty("No instrument rows for the selected period")
    before_period = _year_ago(df, period)
    before = _slice(df, before_period, RETAIL_CODES) if before_period else None

    fig = go.Figure()
    if before is not None and not before.empty:
        fig.add_trace(go.Bar(
            y=before["label"], x=before["volume_mn"], orientation="h", name=before_period,
            marker_color="rgba(138,148,166,0.45)",
            hovertemplate="%{y}<br>%{x:,.1f} Mn<extra></extra>",
        ))
    fig.add_trace(go.Bar(
        y=now["label"], x=now["volume_mn"], orientation="h", name=period,
        marker_color=[ACCENT if c == "2.6" else "rgba(31,111,235,0.65)" for c in now["code"]],
        text=[f"{v:,.0f} Mn" for v in now["volume_mn"]], textposition="outside",
        hovertemplate="%{y}<br>%{x:,.1f} Mn<extra></extra>",
    ))
    fig.update_layout(**LAYOUT, height=460, barmode="group", hovermode="closest",
                      title=f"Retail payment volume by instrument ({period})",
                      xaxis_title="Volume (Mn)")
    fig.update_yaxes(autorange="reversed")
    return fig


# --------------------------------------------------------------------------- #
# 4. Share of retail volume
# --------------------------------------------------------------------------- #
def donut_chart_method_distribution(df: pd.DataFrame, period: str | None = None) -> go.Figure:
    """How the latest month's retail transactions split across instruments."""
    if df is None or len(df) == 0:
        return _empty("No instrument-level data available")
    period = period or latest_period(df)
    sub = _slice(df, period, RETAIL_CODES)
    sub = sub[sub["volume_mn"] > 0]
    if sub.empty:
        return _empty("No instrument rows for the selected period")

    fig = go.Figure(go.Pie(
        labels=sub["label"], values=sub["volume_mn"], hole=0.55,
        marker=dict(colors=SEQ), sort=True, textinfo="label+percent",
        textposition="outside",
        hovertemplate="%{label}<br>%{value:,.1f} Mn (%{percent})<extra></extra>",
    ))
    fig.update_layout(**LAYOUT, height=460, hovermode="closest", showlegend=False,
                      title=f"Share of retail transactions - {period}")
    return fig


# --------------------------------------------------------------------------- #
# 5. Volume against value
# --------------------------------------------------------------------------- #
def scatter_volume_vs_value(df: pd.DataFrame, period: str | None = None) -> go.Figure:
    """Every instrument placed by volume and value - the small-ticket / big-ticket split."""
    if df is None or len(df) == 0:
        return _empty("No instrument-level data available")
    period = period or latest_period(df)
    sub = _slice(df, period, INCLUDE_WHOLESALE)
    sub = sub[(sub["volume_mn"] > 0) & (sub["value_cr"] > 0)]
    if sub.empty:
        return _empty("No instrument rows for the selected period")

    fig = go.Figure(go.Scatter(
        x=sub["volume_mn"], y=sub["value_cr"], mode="markers+text",
        text=sub["label"], textposition="top center",
        textfont=dict(size=11),
        marker=dict(size=np.clip(np.log10(sub["avg_ticket_size"].fillna(1)) * 5, 8, 34),
                    color=SEQ[: len(sub)], line=dict(width=1, color="white")),
        customdata=np.stack([sub["avg_ticket_size"].fillna(0)], axis=-1),
        hovertemplate="%{text}<br>Volume %{x:,.1f} Mn<br>Value Rs %{y:,.0f} Cr"
                      "<br>Avg ticket Rs %{customdata[0]:,.0f}<extra></extra>",
    ))
    fig.update_layout(**LAYOUT, height=470, hovermode="closest",
                      title=f"Volume against value by instrument - {period} (log scale)",
                      xaxis_title="Volume (Mn, log)", yaxis_title="Value (Rs Cr, log)")
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log")
    return fig


# --------------------------------------------------------------------------- #
# 6. Year-on-year growth
# --------------------------------------------------------------------------- #
def growth_chart_instruments(df: pd.DataFrame, period: str | None = None) -> go.Figure:
    """Year-on-year change in volume and value for each retail instrument."""
    if df is None or len(df) == 0:
        return _empty("No instrument-level data available")
    period = period or latest_period(df)
    before_period = _year_ago(df, period)
    if before_period is None:
        return _empty("No same-month figure from a year earlier in this table")

    now = _slice(df, period, RETAIL_CODES).set_index("code")
    before = _slice(df, before_period, RETAIL_CODES).set_index("code")
    codes = [c for c in RETAIL_CODES if c in now.index and c in before.index]
    if not codes:
        return _empty("No overlapping instruments between the two periods")

    vol_growth = [(now.loc[c, "volume_mn"] / before.loc[c, "volume_mn"] - 1) * 100
                  if before.loc[c, "volume_mn"] else np.nan for c in codes]
    val_growth = [(now.loc[c, "value_cr"] / before.loc[c, "value_cr"] - 1) * 100
                  if before.loc[c, "value_cr"] else np.nan for c in codes]
    labels = [LABELS.get(c, c) for c in codes]

    fig = go.Figure()
    fig.add_trace(go.Bar(y=labels, x=vol_growth, orientation="h", name="Volume %",
                         marker_color=[NEGATIVE if (g or 0) < 0 else ACCENT for g in vol_growth],
                         hovertemplate="%{y}<br>Volume %{x:+.1f}%<extra></extra>"))
    fig.add_trace(go.Bar(y=labels, x=val_growth, orientation="h", name="Value %",
                         marker_color="rgba(242,153,74,0.75)",
                         hovertemplate="%{y}<br>Value %{x:+.1f}%<extra></extra>"))
    fig.add_vline(x=0, line_width=1, line_color=MUTED)
    fig.update_layout(**LAYOUT, height=470, barmode="group", hovermode="closest",
                      title=f"Year-on-year growth, {before_period} to {period}",
                      xaxis_title="Change (%)")
    fig.update_yaxes(autorange="reversed")
    return fig


# --------------------------------------------------------------------------- #
# 7. Fraud trend
# --------------------------------------------------------------------------- #
def fraud_trend_chart(df: pd.DataFrame) -> go.Figure:
    """Monthly fraud value against the fraud-to-sales ratio (FTS, basis points)."""
    if df is None or len(df) == 0:
        return _empty("No fraud data available")
    d = df.copy()
    d["month"] = pd.to_datetime(d["month"], errors="coerce")
    d = d.dropna(subset=["month"]).sort_values("month")
    if d.empty:
        return _empty("No fraud data available")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=d["month"], y=d["fraud_value_cr"], name="Fraud value (Rs Cr)",
                         marker_color="rgba(235,87,87,0.55)",
                         hovertemplate="%{x|%b %Y}<br>Rs %{y:,.0f} Cr<extra></extra>"),
                  secondary_y=False)
    if "fts_bps" in d.columns:
        fig.add_trace(go.Scatter(x=d["month"], y=d["fts_bps"], name="FTS (bps)",
                                 mode="lines+markers", line=dict(color=ACCENT, width=2),
                                 marker=dict(size=4),
                                 hovertemplate="%{x|%b %Y}<br>%{y:.3f} bps<extra></extra>"),
                      secondary_y=True)
    fig.update_layout(**LAYOUT, height=430,
                      title="Domestic payment frauds: value and fraud-to-sales ratio")
    fig.update_yaxes(title_text="Fraud value (Rs Cr)", secondary_y=False)
    fig.update_yaxes(title_text="FTS (basis points)", secondary_y=True)
    return fig


# --------------------------------------------------------------------------- #
# 8. Acceptance infrastructure
# --------------------------------------------------------------------------- #
INFRA_METRICS = {
    "UPI QR": "UPI QR codes",
    "Number of PoS Terminals": "PoS terminals",
    "Number of Micro ATMs": "Micro ATMs",
    "Number of Cards": "Cards issued",
}


def infrastructure_chart(df: pd.DataFrame) -> go.Figure:
    """Acceptance points indexed to 100 at the earliest period in the table."""
    if df is None or len(df) == 0:
        return _empty("No infrastructure data available")
    d = df[df["metric"].isin(INFRA_METRICS)].copy()
    if d.empty:
        return _empty("No infrastructure data available")
    d["label"] = d["metric"].map(INFRA_METRICS)

    pivot = d.pivot_table(index="period_label", columns="label", values="value_lakh", aggfunc="mean")
    order = sorted(pivot.index, key=lambda x: pd.to_datetime(x, format="%b %Y", errors="coerce")
                   if not str(x).startswith("FY") else pd.Timestamp.max)
    pivot = pivot.reindex(order)
    base = pivot.iloc[0]
    indexed = (pivot / base * 100).round(1)

    fig = go.Figure()
    for i, col in enumerate(indexed.columns):
        fig.add_trace(go.Scatter(
            x=indexed.index, y=indexed[col], mode="lines+markers", name=col,
            line=dict(color=SEQ[i % len(SEQ)], width=3), marker=dict(size=8),
            hovertemplate="%{x}<br>" + col + ": index %{y:.0f}<extra></extra>",
        ))
    fig.add_hline(y=100, line_width=1, line_dash="dot", line_color=MUTED)
    fig.update_layout(**LAYOUT, height=420,
                      title="Acceptance infrastructure, indexed to the first period = 100",
                      yaxis_title="Index (first period = 100)")
    return fig


# --------------------------------------------------------------------------- #
# Extra views (kept for completeness)
# --------------------------------------------------------------------------- #
def area_chart_total_volume(df: pd.DataFrame) -> go.Figure:
    """Cumulative UPI transactions across the selected period."""
    d = _prepare_series(df)
    if d.empty or "upi_volume" not in d.columns:
        return _empty("No UPI volume data in the selected range")
    cum = d["upi_volume"].fillna(0).cumsum()
    fig = go.Figure(go.Scatter(x=d["month"], y=cum, mode="lines", fill="tozeroy",
                               line=dict(color=ACCENT, width=2),
                               fillcolor="rgba(31,111,235,0.15)",
                               hovertemplate="%{x|%b %Y}<br>%{y:,.0f} Mn cumulative<extra></extra>"))
    fig.update_layout(**LAYOUT, height=380, title="Cumulative UPI transactions (millions)",
                      yaxis_title="Cumulative volume (Mn)")
    return fig


def heatmap_monthly_patterns(df: pd.DataFrame) -> go.Figure:
    """Year x month grid of UPI volume. Needs a year of history to be informative."""
    d = _prepare_series(df)
    if d.empty or "upi_volume" not in d.columns:
        return _empty("No UPI volume data in the selected range")
    tmp = d.assign(year=d["month"].dt.year, month_no=d["month"].dt.month)
    grid = tmp.pivot_table(index="year", columns="month_no", values="upi_volume", aggfunc="mean")
    grid = grid.reindex(columns=range(1, 13))
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure(go.Heatmap(z=grid.values, x=months, y=[str(y) for y in grid.index],
                               colorscale="Blues", colorbar=dict(title="Mn"),
                               hovertemplate="%{y} %{x}<br>%{z:,.0f} Mn<extra></extra>"))
    fig.update_layout(**LAYOUT, height=320, hovermode="closest",
                      title="UPI volume by year and month (millions)", yaxis_title=None)
    fig.update_yaxes(type="category")
    return fig


__all__ = [
    "line_chart_upi_volume",
    "dual_axis_upi",
    "bar_chart_payment_methods",
    "donut_chart_method_distribution",
    "scatter_volume_vs_value",
    "growth_chart_instruments",
    "fraud_trend_chart",
    "infrastructure_chart",
    "area_chart_total_volume",
    "heatmap_monthly_patterns",
    "latest_period",
    "RETAIL_CODES",
    "LABELS",
]
