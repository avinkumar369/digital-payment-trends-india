"""Streamlit dashboard for Digital Payment Trends project.

This app loads the processed dataset, shows key performance indicators (KPIs), and displays
interactive Plotly visualisations defined in `src.visualizations`.
"""
import streamlit as st
import pandas as pd
from pathlib import Path

# Set page config
st.set_page_config(page_title="Digital Payment Trends Dashboard", layout="wide")

# Load data
# Correct path – go up one level from the script’s folder to the repository root
DATA_PATH = Path(__file__).parent.parent / "data" / "processed" / "upi_merged.csv"
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["month"])
    return df

df = load_data()

# Sidebar filters
st.sidebar.header("Filters")
min_date = df["month"].min()
max_date = df["month"].max()
date_range = st.sidebar.date_input("Select date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    mask = (df["month"] >= pd.Timestamp(start_date)) & (df["month"] <= pd.Timestamp(end_date))
    df_filtered = df.loc[mask]
else:
    df_filtered = df.copy()

# KPI calculations
total_volume = df_filtered["upi_volume"].sum()
total_value = df_filtered["upi_value"].sum()
avg_daily_volume = df_filtered["upi_avg_daily_volume"].mean()
avg_daily_value = df_filtered["upi_avg_daily_value"].mean()

# KPI display
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total UPI Volume (Mn)", f"{total_volume:,.2f}")
col2.metric("Total UPI Value (Cr)", f"{total_value:,.2f}")
col3.metric("Avg Daily Volume (Mn)", f"{avg_daily_volume:,.2f}")
col4.metric("Avg Daily Value (Cr)", f"{avg_daily_value:,.2f}")

# Load visualisation functions
from src.visualizations import (
    line_chart_upi_volume,
    bar_chart_payment_methods,
    area_chart_total_volume,
    donut_chart_method_distribution,
    heatmap_monthly_patterns,
    scatter_volume_vs_value,
    dual_axis_upi,
)

st.subheader("UPI Transaction Volume Over Time")
st.plotly_chart(line_chart_upi_volume(df_filtered), use_container_width=True)

st.subheader("Payment Methods Volume Distribution")
st.plotly_chart(bar_chart_payment_methods(df_filtered), use_container_width=True)

st.subheader("Cumulative Transaction Volume")
st.plotly_chart(area_chart_total_volume(df_filtered), use_container_width=True)

st.subheader("Method Distribution (Latest Month)")
st.plotly_chart(donut_chart_method_distribution(df_filtered), use_container_width=True)

st.subheader("Monthly Volume Heatmap")
st.plotly_chart(heatmap_monthly_patterns(df_filtered), use_container_width=True)

st.subheader("UPI Volume vs Value Scatter")
st.plotly_chart(scatter_volume_vs_value(df_filtered), use_container_width=True)

st.subheader("Dual Axis: Volume & Value")
st.plotly_chart(dual_axis_upi(df_filtered), use_container_width=True)

st.caption("Data source: NPCI UPI statistics and RBI payment‑system indicators (processed in `data/processed/upi_merged.csv`).")
