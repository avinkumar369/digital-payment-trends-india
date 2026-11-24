# src/eda.py
"""Exploratory Data Analysis utilities.

Functions here operate on the processed DataFrame produced by
``src.preprocessing`` and return summary tables or Plotly figures ready for
visualisation.
"""
import pandas as pd
import numpy as np
from typing import Tuple

def descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame with basic descriptive statistics for numeric columns.

    The result includes count, mean, std, min, 25%, 50% (median), 75%, max.
    """
    numeric = df.select_dtypes(include=[np.number])
    return numeric.describe().transpose()

def monthly_growth(df: pd.DataFrame, column: str) -> pd.Series:
    """Compute month‑on‑month percentage growth for a given column.
    Returns a Series indexed by ``month`` with ``NaN`` for the first entry.
    """
    growth = df.set_index("month")[column].pct_change() * 100
    growth.name = f"{column}_mom_growth"
    return growth

def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Correlation matrix for numeric columns (Pearson).
    """
    numeric = df.select_dtypes(include=[np.number])
    return numeric.corr()
