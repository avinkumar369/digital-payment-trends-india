# src/visualizations.py
"""Visualization utilities using Plotly.

All functions accept the processed DataFrame (output of ``preprocessing.merge_datasets``)
and return a Plotly ``Figure`` object ready to be displayed in Streamlit or a Jupyter
notebook.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def line_chart_upi_volume(df: pd.DataFrame):
    """Line chart – UPI transaction volume over time.
    Requires a column named ``upi_volume``.
    """
    fig = px.line(df, x="month", y="upi_volume", title="UPI Transaction Volume Over Time")
    fig.update_layout(xaxis_title="Month", yaxis_title="Number of Transactions")
    return fig

def bar_chart_payment_methods(df: pd.DataFrame):
    """Bar chart – total transaction volume for each payment method.
    Aggregates columns that contain the word ``volume`` (excluding ``upi_volume``).
    """
    volume_cols = [c for c in df.columns if "volume" in c and c != "upi_volume"]
    totals = df[volume_cols].sum().reset_index()
    totals.columns = ["method", "total_volume"]
    # Add UPI as a method as well
    upi_total = df["upi_volume"].sum()
    totals = pd.concat([totals, pd.DataFrame({"method": ["UPI"], "total_volume": [upi_total]})], ignore_index=True)
    fig = px.bar(totals, x="method", y="total_volume", title="Total Transaction Volume by Payment Method")
    fig.update_layout(xaxis_title="Payment Method", yaxis_title="Total Volume")
    return fig

def area_chart_total_volume(df: pd.DataFrame):
    """Area chart – cumulative digital‑payment transaction volume over time.
    Stacks all volume columns.
    """
    volume_cols = [c for c in df.columns if "volume" in c]
    stacked = df.melt(id_vars="month", value_vars=volume_cols, var_name="method", value_name="volume")
    fig = px.area(stacked, x="month", y="volume", color="method",
                  title="Cumulative Digital Payment Transaction Volume Over Time")
    fig.update_layout(xaxis_title="Month", yaxis_title="Volume")
    return fig

def donut_chart_method_distribution(df: pd.DataFrame):
    """Donut chart – distribution of transaction volume across payment methods.
    Uses the most recent month available in the data.
    """
    latest = df["month"].max()
    latest_row = df[df["month"] == latest].iloc[0]
    volume_cols = [c for c in df.columns if "volume" in c]
    values = [latest_row[c] for c in volume_cols]
    labels = [c.replace("_volume", "").upper() for c in volume_cols]
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
    fig.update_layout(title=f"Payment Method Volume Distribution ({latest.strftime('%B %Y')})")
    return fig

def heatmap_monthly_patterns(df: pd.DataFrame):
    """Heatmap – month‑year matrix of total transaction volume.
    Rows: year, Columns: month number.
    """
    df = df.copy()
    df["year"] = df["month"].dt.year
    df["month_num"] = df["month"].dt.month
    volume_cols = [c for c in df.columns if "volume" in c]
    # Sum all volume columns for a single metric
    df["total_volume"] = df[volume_cols].sum(axis=1)
    pivot = df.pivot(index="year", columns="month_num", values="total_volume")
    fig = go.Figure(data=go.Heatmap(z=pivot.values, x=[f"{m}" for m in pivot.columns], y=[str(y) for y in pivot.index],
                                   colorscale="Viridis"))
    fig.update_layout(title="Monthly Transaction Volume Heatmap", xaxis_title="Month", yaxis_title="Year")
    return fig

def scatter_volume_vs_value(df: pd.DataFrame):
    """Scatter plot – relationship between transaction volume and value for UPI.
    Requires ``upi_volume`` and ``upi_value`` columns.
    """
    fig = px.scatter(df, x="upi_volume", y="upi_value", trendline="ols",
                     title="UPI Volume vs. Value")
    fig.update_layout(xaxis_title="Transaction Volume", yaxis_title="Transaction Value (₹ Crores)")
    return fig

def dual_axis_upi(df: pd.DataFrame):
    """Combined line chart – UPI volume (bars) and value (line) over time.
    """
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["month"], y=df["upi_volume"], name="Volume"))
    fig.add_trace(go.Line(x=df["month"], y=df["upi_value"], name="Value", yaxis="y2"))
    fig.update_layout(
        title="UPI Transaction Volume and Value Over Time",
        xaxis_title="Month",
        yaxis=dict(title="Volume", side="left"),
        yaxis2=dict(title="Value (₹ Crores)", overlaying="y", side="right"),
    )
    return fig
