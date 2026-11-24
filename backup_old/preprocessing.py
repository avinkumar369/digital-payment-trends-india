"""Data preprocessing utilities for the Digital Payment Trends project.

This module cleans the raw NPCI and RBI CSV files and merges them into a
single tidy DataFrame ready for analysis.
"""
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

def clean_npci(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the NPCI UPI dataset.

    - Remove the UTF‑8 BOM (ï»¿) from the first column name.
    - Standardise column names to snake_case.
    - Parse the ``Month`` string (e.g. ``March-2026``) to a ``datetime``
      representing the first day of the month.
    - Convert all numeric columns to ``float``.
    """
    df = df.copy()
    # Fix column names – strip BOM and whitespace, lower‑case, replace spaces with underscores
    df.columns = [c.replace('ï»¿', '').strip().lower().replace(' ', '_').replace('(', '').replace(')', '') for c in df.columns]
    # Ensure month column name is "month"
    if "month" not in df.columns:
        raise KeyError("NPCI data must contain a 'Month' column after cleaning")
    # Convert month strings like "March-2026" to datetime (first day of month)
    df["month"] = pd.to_datetime(df["month"], format='%B-%Y', errors='coerce')
    # Convert numeric columns (those containing volume or value) to float
    for col in [c for c in df.columns if "volume" in c or "value" in c]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    # Rename columns to standardized names
    rename_map = {
        'volume_in_mn.': 'upi_volume',
        'avg._daily_volume_in_mn.': 'upi_avg_daily_volume',
        'value_in_cr.': 'upi_value',
        'avg._daily_value_in_cr.': 'upi_avg_daily_value',
    }
    df = df.rename(columns=rename_map)
    return df

def clean_rbi(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the RBI payment‑system indicators dataset.

    The CSV contains several header rows and many empty columns. This function:
    1. Drops rows that are completely empty.
    2. Uses the first non‑empty row that contains the text "Financial Market Infrastructures"
       as the header row.
    3. Renames columns to snake_case.
    4. Converts any column that can be numeric to ``float``.
    """
    df = df.copy()
    # Drop completely empty rows
    df = df.dropna(how='all').reset_index(drop=True)
    # Find header row index – look for a row where the first cell contains the phrase
    header_idx = None
    for i, val in enumerate(df.iloc[:, 0].astype(str)):
        if "Financial Market Infrastructures" in val:
            header_idx = i
            break
    if header_idx is None:
        # fallback: use the first row that has any non‑numeric entry
        for i, val in enumerate(df.iloc[:, 0].astype(str)):
            if val and not val.replace('.', '', 1).isdigit():
                header_idx = i
                break
    if header_idx is None:
        header_idx = 0
    # Set the header row
    df.columns = df.iloc[header_idx]
    # Drop rows up to and including the header row
    df = df.drop(index=range(header_idx + 1)).reset_index(drop=True)
    # Clean column names
    df.columns = [str(c).strip().lower().replace(' ', '_').replace('(', '').replace(')', '') for c in df.columns]
    # Remove duplicate column names that may arise from malformed headers
    df = df.loc[:, ~df.columns.duplicated()]
    # Convert possible numeric columns to float
    for col in df.columns:
        # Convert column to numeric where possible, coercing errors to NaN
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def merge_datasets(npci: pd.DataFrame, rbi: pd.DataFrame) -> pd.DataFrame:
    """Merge NPCI and RBI data on the ``month`` column.

    The NPCI data provides the primary monthly timeline. RBI data does not
    contain a month column, so we perform a left join on month (if present) and
    otherwise attach aggregated RBI totals as additional KPI columns.
    """
    # If RBI contains a month column after cleaning, merge on it; otherwise aggregate.
    if "month" in rbi.columns:
        merged = pd.merge(npci, rbi, on="month", how="left", suffixes=("_npci", "_rbi"))
    else:
        # Aggregate numeric RBI columns (sum across all rows) to single values
        numeric_cols = [c for c in rbi.select_dtypes(include='number').columns]
        agg = {c: 'sum' for c in numeric_cols}
        rbi_agg = rbi.agg(agg).to_dict()
        merged = npci.copy()
        for k, v in rbi_agg.items():
            merged[f"rbi_{k}"] = v
    merged = merged.sort_values("month").reset_index(drop=True)
    return merged

def save_processed(df: pd.DataFrame, filename: str = "upi_merged.csv") -> Path:
    """Save the cleaned, merged DataFrame to the processed data folder.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / filename
    df.to_csv(out_path, index=False)
    return out_path
