# src/data_collection.py
"""Data collection utilities.

This module defines functions that load the raw CSV files produced in Phase 1.
The actual file paths are fixed relative to the project root, but the functions
gracefully handle the situation where the files are not yet present – they raise
a clear ``FileNotFoundError`` with instructions.
"""
import os
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

def load_npci_data() -> pd.DataFrame:
    """Load the NPCI UPI transaction CSV.

    Returns
    -------
    pd.DataFrame
        DataFrame with at least ``Month``, ``UPI_Volume`` and ``UPI_Value`` columns.
    """
    csv_path = RAW_DATA_DIR / "upi_npci.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"NPCI data not found at {csv_path}. Please place the CSV file there."
        )
    df = pd.read_csv(csv_path)
    return df

def load_rbi_data() -> pd.DataFrame:
    """Load the RBI payment‑system indicators CSV.

    Returns
    -------
    pd.DataFrame
        DataFrame containing monthly statistics for NEFT, IMPS, RTGS, etc.
    """
    csv_path = RAW_DATA_DIR / "rbi_payments.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"RBI data not found at {csv_path}. Please place the CSV file there."
        )
    df = pd.read_csv(csv_path)
    return df
